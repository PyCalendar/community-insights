from datetime import datetime, timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone
from encrypted_fields.fields import EncryptedCharField
from ordered_model.models import OrderedModel

HOUR = timedelta(hours=1)
GITHUB_POINTS = 5000  # per hour, until GitHub tells the limit of the token


def percent_of(points: int, percent: int) -> int:
    """A percentage of points, rounded to whole points."""
    return round(points * percent / 100)


class AccessToken(OrderedModel):
    """A GitHub token of the user, a friend or another account.

    Tokens are used in their order (django-ordered-model), the token itself is encrypted in the
    database (django-fernet-encrypted-fields). The owner uses up to `max_percent` of the points
    per hour; `shared_percent` of that is given to everybody else on this site. What is not used
    stays as a reserve with GitHub.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.CASCADE, related_name="access_tokens")
    label = models.CharField(max_length=100, blank=True)
    token = EncryptedCharField(max_length=255)
    login = models.CharField(max_length=100)  # whose token it is on GitHub
    linked = models.BooleanField(default=False)  # the linked GitHub account (django-allauth)
    max_percent = models.PositiveSmallIntegerField(default=100)  # of the points per hour
    shared_percent = models.PositiveSmallIntegerField(default=10)  # of the maximum
    expires_at = models.DateTimeField(null=True, blank=True)  # None: never or unknown
    # what GitHub said in the last answer
    rate_limit = models.IntegerField(null=True, blank=True)
    rate_remaining = models.IntegerField(null=True, blank=True)
    rate_reset_at = models.DateTimeField(null=True, blank=True)
    # points used in the current hour: by anybody, and by others than the owner
    hour_started = models.DateTimeField(null=True, blank=True)
    used_in_hour = models.PositiveIntegerField(default=0)
    used_by_others_in_hour = models.PositiveIntegerField(default=0)
    last_test = models.JSONField(default=dict, blank=True)  # {"checked", "missing", "ok", "total"}
    last_error = models.TextField(blank=True)
    last_error_code = models.CharField(max_length=60, blank=True)  # a class of errors/
    created = models.DateTimeField(default=timezone.now)

    order_with_respect_to = "user"

    class Meta(OrderedModel.Meta):
        pass

    def __str__(self):
        return self.label or f"token of {self.login}"

    # the numbers of the sliders (static/js/token-sliders.js computes the same)

    @property
    def points_per_hour(self) -> int:
        """The points GitHub gives the token per hour (5000 until it told)."""
        return self.rate_limit or GITHUB_POINTS

    @property
    def max_points(self) -> int:
        """The points per hour this site may use (the first slider)."""
        return percent_of(self.points_per_hour, self.max_percent)

    @property
    def reserve(self) -> int:
        """Points that stay with GitHub: the token is not used below them."""
        return self.points_per_hour - self.max_points

    @property
    def shared_points(self) -> int:
        """The points per hour others on this site may use (the second slider)."""
        return percent_of(self.max_points, self.shared_percent)

    def new_hour(self, now: datetime) -> bool:
        """Whether the hour of the counters is over."""
        return self.hour_started is None or now - self.hour_started >= HOUR

    def left_at_github(self, now: datetime) -> int | None:
        """Points this site may still use, after the reserve; None if unknown."""
        renewed = self.rate_reset_at and self.rate_reset_at <= now
        if self.rate_remaining is None or renewed:
            return None
        return max(0, self.rate_remaining - self.reserve)

    def owner_left(self, now: datetime) -> int:
        """Points the owner may still use this hour, within the reserve."""
        used = 0 if self.new_hour(now) else self.used_in_hour
        left = max(0, self.max_points - used)
        github = self.left_at_github(now)
        return left if github is None else min(left, github)

    def others_left(self, now: datetime) -> int:
        """Points others may still use this hour, within the reserve."""
        used = 0 if self.new_hour(now) else self.used_by_others_in_hour
        return min(max(0, self.shared_points - used), self.owner_left(now))

    def count(self, now: datetime, by_others: bool) -> None:
        """One point used, by the owner or by somebody else."""
        if self.new_hour(now):
            self.hour_started, self.used_in_hour, self.used_by_others_in_hour = now, 0, 0
        self.used_in_hour += 1
        if by_others:
            self.used_by_others_in_hour += 1
