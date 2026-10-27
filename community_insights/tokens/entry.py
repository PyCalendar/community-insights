from datetime import datetime, timedelta

from ..models import AccessToken
from .allowance import HourAllowance

HOUR = timedelta(hours=1)


class Entry:
    """A token in a pool, with the client that uses it.

    A token in a pool, with the client that uses it: the linked GitHub account (no own limit),
    an own AccessToken (up to its maximum, then the allowance of the hour) or the token of
    somebody else (its shared points).
    """

    def __init__(
        self,
        label: str,
        client,
        stored: AccessToken | None = None,
        shared: bool = False,
        allowance: HourAllowance | None = None,
    ):
        """A token in a pool, with the limits of this site and of GitHub.

        Args:
            label: How the token is named in messages.
            client: The GitHub client with the token.
            stored: The stored token with its limits, None for one that is not stored.
            shared: True for the points somebody else shares with this site.
            allowance: The points the user allowed above the limits for this hour.
        """
        self.label, self.client, self.stored = label, client, stored
        self.shared = shared
        self.allowance = allowance or HourAllowance(None)
        if stored is not None:
            client.rate.remaining = stored.rate_remaining
            client.rate.reset_at = stored.rate_reset_at

    def left(self, now: datetime) -> int | None:
        """Points this entry may use now; None for no limit of this site.

        Args:
            now: The time now.

        Returns:
            The points, or None.
        """
        stored = self.stored
        if stored is None:
            return None
        if self.shared:
            return stored.others_left(now)
        left = stored.owner_left(now)
        if left == 0 and stored.left_at_github(now) != 0:
            return self.allowance.left(now)
        return left

    def github_budget(self, now: datetime) -> int | None:
        """Points left at GitHub; None if unknown or renewed.

        Args:
            now: The time now.

        Returns:
            The points, or None.
        """
        rate = self.client.rate
        if rate.remaining is None or (rate.reset_at and rate.reset_at <= now):
            return None  # unknown or renewed
        return rate.remaining

    def usable(self, now: datetime) -> bool:
        """Whether the token may be used now.

        Args:
            now: The time now.

        Returns:
            True if neither this site nor GitHub says it has no points left.
        """
        return all(b is None or b > 0 for b in (self.left(now), self.github_budget(now)))

    def expired(self, now: datetime) -> bool:
        """Whether the stored token has expired.

        Args:
            now: The time now.

        Returns:
            True if its expiration date has passed.
        """
        return bool(self.stored and self.stored.expires_at and self.stored.expires_at <= now)

    def available_again(self, now: datetime) -> datetime:
        """When this token can be used again.

        Args:
            now: The time now.

        Returns:
            The time; in an hour if it is not known.
        """
        times = []
        if self.left(now) == 0 and self.stored and self.stored.hour_started:
            times.append(self.stored.hour_started + HOUR)
        if self.github_budget(now) == 0 and self.client.rate.reset_at:
            times.append(self.client.rate.reset_at)
        return max(times) if times else now + HOUR

    def spent(self, now: datetime, error: Exception | None = None) -> None:
        """Count a request of the token, or remember why it failed.

        Args:
            now: The time now.
            error: Why the request failed, None if it worked.
        """
        stored = self.stored
        if stored is None:
            return
        if error is None:
            over = not self.shared and stored.owner_left(now) == 0
            stored.count(now, by_others=self.shared)
            if over:
                self.allowance.spend()
        rate = self.client.rate
        stored.rate_limit = rate.limit or stored.rate_limit
        stored.rate_remaining = rate.remaining
        stored.rate_reset_at = rate.reset_at
        stored.expires_at = rate.expires_at or stored.expires_at
        if not self.shared:  # the errors of a shared token are for its owner only
            stored.last_error = str(error) if error else ""
            stored.last_error_code = getattr(error, "code", "") if error else ""
        stored.save()
