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
    """The error for GitHub refusing a token (HTTP 403 or FORBIDDEN).

    Args:
        message: What GitHub said.

    Returns:
        The error, to raise.
    """
    if "lifetime" in message.lower():
        return TokenLifetimeRefused(message)
    return TokenNotAllowed(message)


def data_of(
    status: int, text: str, body, rate: RateLimit, retry_after: float | None = None
) -> dict:
    """The data of a GraphQL answer.

    Errors that only say that something was not found are no errors: a missing user is None in
    the data. `body` is the parsed JSON, or a ValueError if the answer was no JSON.

    Args:
        status: The HTTP status.
        text: The text of the answer, for the messages.
        body: The parsed JSON, or a ValueError if it was no JSON.
        rate: The rate limit of the token, for when it can be used again.
        retry_after: The seconds GitHub asks to wait, if it says so.

    Returns:
        The data.

    Raises:
        InvalidAPIToken: If GitHub does not accept the token.
        ExpiredAPIToken: If the token has expired.
        TokenLifetimeRefused: If an organisation refuses the token for its lifetime.
        TokenNotAllowed: If the token may not read this.
        RateLimitExceeded: If the points of the token are used up.
        SecondaryRateLimitExceeded: If GitHub asks to slow down.
        GitHubUnreachable: If GitHub answers with a server error.
        GitHubRequestRejected: If GitHub refuses the request.
        GitHubAnswerNotJSON: If the answer is no JSON.
        GraphQLError: If GitHub reports another error of the query.
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
