from datetime import datetime

from ..models import Profile


class HourAllowance:
    """The extra points a user allowed for this hour.

    The extra points a user allowed for this hour, above the maximum of the own tokens; shared
    by all of them.
    """

    def __init__(self, profile: Profile | None):
        self.profile = profile

    def left(self, now: datetime) -> int:
        """Points still allowed above the maximum in this hour."""
        return self.profile.extra_left(now) if self.profile else 0

    def spend(self) -> None:
        """Count a point used of the allowance."""
        if self.profile is None:
            return
        self.profile.extra_used += 1
        self.profile.save(update_fields=["extra_used"])
