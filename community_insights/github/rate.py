from dataclasses import dataclass
from datetime import UTC, datetime

from .headers import header_int, parse_expiration


@dataclass
class RateLimit:
    """The rate limit of a token and when the token expires, as GitHub told in its last answer.

    Attributes:
        limit: The points per hour, None until GitHub told.
        remaining: The points left, None until GitHub told.
        reset_at: When GitHub renews the points.
        expires_at: When the token expires, None for no date or not told.
    """

    limit: int | None = None
    remaining: int | None = None
    reset_at: datetime | None = None
    expires_at: datetime | None = None

    def note(self, headers) -> None:
        """Remember the rate limit and the expiration of the headers of an answer.

        Args:
            headers: The headers of an answer of GitHub.
        """
        self.limit = header_int(headers, "x-ratelimit-limit") or self.limit
        remaining = header_int(headers, "x-ratelimit-remaining")
        if remaining is not None:
            self.remaining = remaining
        reset = header_int(headers, "x-ratelimit-reset")
        if reset is not None:
            self.reset_at = datetime.fromtimestamp(reset, UTC)
        self.expires_at = (
            parse_expiration(headers.get("github-authentication-token-expiration"))
            or self.expires_at
        )

    @property
    def expired(self) -> bool:
        """Whether the token has expired, as far as GitHub told."""
        return bool(self.expires_at and self.expires_at <= datetime.now(UTC))
