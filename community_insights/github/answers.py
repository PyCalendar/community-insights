"""An answer of GitHub becomes data, or the error that explains it."""

from ..errors import (
    ExpiredAPIToken,
    GitHubAnswerNotJSON,
    GitHubRequestRejected,
    GitHubUnreachable,
    GraphQLError,
    InvalidAPIToken,
    RateLimitExceeded,
    SecondaryRateLimitExceeded,
    TokenError,
    TokenLifetimeRefused,
    TokenNotAllowed,
)
from .rate import RateLimit


def refusal(message: str) -> TokenError:
    """The error for GitHub refusing a token (HTTP 403 or FORBIDDEN)."""
    if "lifetime" in message.lower():
        return TokenLifetimeRefused(message)
    return TokenNotAllowed(message)


def data_of(
    status: int, text: str, body, rate: RateLimit, retry_after: float | None = None
) -> dict:
    """The data of a GraphQL answer.

    Errors that only say that something was not found are no errors: a missing user is None in
    the data. `body` is the parsed JSON, or a ValueError if the answer was no JSON.
    """
    if status == 401:
        if rate.expired:
            raise ExpiredAPIToken(f"The token expired on {rate.expires_at:%Y-%m-%d}.")
        raise InvalidAPIToken("GitHub rejected the token: it is wrong, expired or revoked.")
    if status in (403, 429) and (retry_after is not None or "secondary rate limit" in text.lower()):
        raise SecondaryRateLimitExceeded(
            "GitHub asks to slow down.", retry_after=retry_after, reset_at=rate.reset_at
        )
    if status in (403, 429) and (rate.remaining == 0 or "rate limit" in text.lower()):
        raise RateLimitExceeded("The rate limit of the token is used up.", rate.reset_at)
    if status == 403:
        raise refusal(text[:300])
    if status >= 500:
        raise GitHubUnreachable(f"GitHub answered {status}.")
    if status >= 400:
        raise GitHubRequestRejected(f"GitHub answered {status}: {text[:200]}", status=status)
    if isinstance(body, ValueError):
        raise GitHubAnswerNotJSON("GitHub answered with something that is not JSON.") from body
    errors = [e for e in body.get("errors") or [] if e.get("type") != "NOT_FOUND"]
    if any(e.get("type") == "RATE_LIMITED" for e in errors):
        raise RateLimitExceeded("The rate limit of the token is used up.", rate.reset_at)
    forbidden = [e for e in errors if e.get("type") == "FORBIDDEN"]
    if forbidden:
        raise refusal(forbidden[0].get("message", ""))
    if errors:
        raise GraphQLError(errors[0].get("message", "GraphQL error"))
    return body.get("data") or {}
