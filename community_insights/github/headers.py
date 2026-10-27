"""What GitHub says in the headers of its answers."""

from datetime import UTC, datetime


def parse_expiration(value: str | None) -> datetime | None:
    """The time of the header github-authentication-token-expiration.

    The header github-authentication-token-expiration, like "2026-11-30 12:00:00 UTC" or
    "2026-11-30 12:00:00 +0100".

    Args:
        value: The value of the header, or None.

    Returns:
        The time, None if there is none or it cannot be read.
    """
    if not value:
        return None
    for pattern in ("%Y-%m-%d %H:%M:%S %Z", "%Y-%m-%d %H:%M:%S %z"):
        try:
            parsed = datetime.strptime(value.strip(), pattern)
        except ValueError:
            continue
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return None


def header_int(headers, name: str) -> int | None:
    """A header as a whole number; None if it is missing or no number.

    Args:
        headers: The headers.
        name: The name of the header.

    Returns:
        The number.
    """
    try:
        return int(headers.get(name))
    except (TypeError, ValueError):
        return None
