from datetime import datetime, timedelta

from django.conf import settings
from django.db import models

HOUR = timedelta(hours=1)


class Profile(models.Model):
    """Settings of a user."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, models.CASCADE, related_name="profile")
    # A fetch estimated to use more API points than this asks for a limit first.
    fetch_limit = models.PositiveIntegerField(default=5000)
    # sources to offer: [{"name": "owner/name" or "owner", "kind", "stars"}]
    suggestions = models.JSONField(default=list, blank=True)
    suggestions_fetched_at = models.DateTimeField(null=True, blank=True)
    # points of the own tokens allowed above their maximum, for one hour
    extra_points = models.PositiveIntegerField(default=0)
    extra_used = models.PositiveIntegerField(default=0)
    extra_from = models.DateTimeField(null=True, blank=True)
    # a tag next to the locations in countries of Horizon Europe
    show_horizon_europe = models.BooleanField(default=False)

    @classmethod
    def of(cls, user) -> "Profile":
        """The profile of a user, created when needed."""
        return cls.objects.get_or_create(user=user)[0]

    def extra_left(self, now: datetime) -> int:
        """Points still allowed above the maximum of the own tokens in this hour.

        Args:
            now: The time now.

        Returns:
            The points; 0 an hour after they were allowed.
        """
        if self.extra_from is None or now - self.extra_from >= HOUR:
            return 0
        return max(0, self.extra_points - self.extra_used)

    def allow_extra(self, points: int, now: datetime) -> None:
        """Allow more points of the own tokens until an hour from now.

        Args:
            points: How many points.
            now: The time now.
        """
        self.extra_points, self.extra_used, self.extra_from = points, 0, now
