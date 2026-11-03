from datetime import datetime, timedelta

from django.db import models
from django.utils.translation import gettext_lazy as _

from .access_token import AccessToken, percent_of

HOUR = timedelta(hours=1)


def scope_covers(granted: str, wanted: str) -> bool:
    """Whether the public scope of a grant covers the scope of a fetch.

    An owner covers all its repositories.

    Args:
        granted: The scope of the grant, such as ``collective`` or ``plone~volto+django``.
        wanted: The scope the fetch is for.

    Returns:
        True if every part of the wanted scope is in the granted one.

    Examples:
        >>> scope_covers("collective", "collective~icalendar")
        True
        >>> scope_covers("collective~icalendar", "collective")
        False
        >>> scope_covers("a~b+c", "c~d+a~b"), scope_covers("a~b", "a~b+x~y")
        (True, False)
    """
    parts = {part.lower() for part in granted.split("+") if part}
    owners = {part for part in parts if "~" not in part}
    return all(
        part in parts or part.split("~")[0] in owners
        for part in (p.lower() for p in wanted.split("+"))
    )


class TokenGrant(models.Model):
    """A public use of a token that its owner allows, with its own share of the points.

    Everybody on this site (the points shared for all fetches), or for a public scope: its
    badges (of one person or all), its public pages, or the fetches visitors start there. Each
    grant may use its percent of the points the site may use of the token per hour.
    """

    EVERYBODY, BADGES, PAGES, VISITORS = "everybody", "badges", "pages", "visitors"
    KINDS = [
        (EVERYBODY, _("everybody on this site")),
        (BADGES, _("badges of replies")),
        (PAGES, _("public pages")),
        (VISITORS, _("fetches of visitors")),
    ]
    token = models.ForeignKey(AccessToken, models.CASCADE, related_name="grants")
    kind = models.CharField(max_length=10, choices=KINDS)
    scope = models.CharField(max_length=300, blank=True)  # "" for everybody
    login = models.CharField(max_length=100, blank=True)  # a badge of one person; "" for all
    percent = models.PositiveSmallIntegerField(default=10)  # of the maximum of the token
    hour_started = models.DateTimeField(null=True, blank=True)
    used_in_hour = models.PositiveIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["token", "kind", "scope", "login"]

    def __str__(self):
        return f"{self.token}: {self.kind} {self.scope} {self.login}".strip()

    @property
    def points(self) -> int:
        """The points per hour this grant may use."""
        return percent_of(self.token.max_points, self.percent)

    def used(self, now: datetime) -> int:
        """Points used in this hour.

        Args:
            now: The time now.

        Returns:
            The points.
        """
        if self.hour_started is None or now - self.hour_started >= HOUR:
            return 0
        return self.used_in_hour

    def left(self, now: datetime) -> int:
        """Points this grant may still use this hour, within what the token has left.

        Args:
            now: The time now.

        Returns:
            The points.
        """
        return min(max(0, self.points - self.used(now)), self.token.owner_left(now))

    def count(self, now: datetime) -> None:
        """One point used.

        Args:
            now: The time now.
        """
        if self.hour_started is None or now - self.hour_started >= HOUR:
            self.hour_started, self.used_in_hour = now, 0
        self.used_in_hour += 1

    def covers(self, use) -> bool:
        """Whether a fetch may use this grant.

        Args:
            use: What the fetch is for (``tokens.Use``); None for an ordinary fetch.

        Returns:
            True for everybody; otherwise for the same kind in the scope, and for one
            person's badge only for that person.
        """
        if self.kind == self.EVERYBODY:
            return True
        if use is None or use.kind != self.kind or not scope_covers(self.scope, use.scope):
            return False
        return not self.login or self.login.lower() == use.login.lower()
