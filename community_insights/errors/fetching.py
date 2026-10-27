"""Errors that stop a fetch from GitHub."""

from datetime import datetime

from django.utils.translation import gettext_lazy as _

from .base import CommunityError


class FetchStopped(CommunityError):
    """A fetch from GitHub stopped before it read everything.

    What was read is kept. Read from GitHub again to continue.
    """

    title = _("The fetch stopped")


class FetchLimitReached(FetchStopped):
    """The limit of API points for this fetch is reached.

    What was read is kept; the page shows how complete the data is. Read from
    GitHub again, with a higher limit, to get the rest.
    """

    title = _("Limit of API points reached")


class AllTokensUsedUp(FetchStopped):
    """All tokens have used up their points for now.

    The fetch waits and goes on when GitHub renews the points, at the time
    shown. Add more tokens to read faster, or raise the hourly limits of your
    tokens on the page *GitHub access*.
    """

    title = _("All tokens used up for now")

    def __init__(self, detail: str = "", reset_at: datetime | None = None, **context):
        super().__init__(detail, **context)
        self.reset_at = reset_at


class FetchCancelled(FetchStopped):
    """The fetch was cancelled.

    Somebody cancelled it on the page *Downloads*. What was read is kept.
    """

    title = _("Cancelled")
