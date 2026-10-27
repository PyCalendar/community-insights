"""Errors that stop a fetch from GitHub."""

from datetime import datetime

from django.utils.translation import gettext_lazy as _

from .base import CommunityError


class FetchStopped(CommunityError):
    """A fetch from GitHub stopped before it read everything.

    What was read is kept. Read from GitHub again to continue.

    How data is fetched: :doc:`/explanation/pipeline`.
    """

    title = _("The fetch stopped")
    guide = "explanation/pipeline.html"
    guide_title = _("How data is fetched")


class VisitorLimitReached(CommunityError):
    """Visitors without an account did this too often from this address in this hour.

    Visitors share the tokens people donated to the site, so each address may
    add and read only some repositories per hour (``VISITOR_SUBMITS_PER_HOUR``
    and ``VISITOR_FETCHES_PER_HOUR``). Wait for the next hour, or sign up and
    add a token of your own: people with an account have no such limit.

    Without an account: :doc:`/how-to/use`.
    """

    title = _("Too many requests from this address")
    guide = "how-to/use.html#without-an-account"
    guide_title = _("Without an account")


class UserItemsLimitReached(CommunityError):
    """The projects of your account would hold more pull requests and issues than allowed.

    Each account may keep a number of pull requests and issues in the
    repositories of its projects (``USER_MAX_ITEMS``), so that one account does
    not fill the database of everybody. Remove projects you do not need on the
    dashboard, or ask the administrators of the site for more.

    The settings of the site: :doc:`/reference/configuration`.
    """

    title = _("Too many pull requests and issues for your account")
    guide = "reference/configuration.html"
    guide_title = _("The settings of the site")


class FetchLimitReached(FetchStopped):
    """The limit of API points for this fetch is reached.

    What was read is kept; the page shows how complete the data is. Read from
    GitHub again, with a higher limit, to get the rest.

    API points and limits: :doc:`/how-to/tokens`.
    """

    title = _("Limit of API points reached")
    guide = "how-to/tokens.html#points-and-limits"
    guide_title = _("API points and limits")


class AllTokensUsedUp(FetchStopped):
    """All tokens have used up their points for now.

    The fetch waits and goes on when GitHub renews the points, at the time
    shown. Add more tokens to read faster, or raise the hourly limits of your
    tokens on the page *GitHub access*.

    API points and limits: :doc:`/how-to/tokens`.
    """

    title = _("All tokens used up for now")
    guide = "how-to/tokens.html#points-and-limits"
    guide_title = _("API points and limits")

    def __init__(self, detail: str = "", reset_at: datetime | None = None, **context):
        """The tokens have no points left now.

        Args:
            detail: What happened.
            reset_at: When a token can be used again.
            **context: More about it.
        """
        super().__init__(detail, **context)
        self.reset_at = reset_at


class FetchCancelled(FetchStopped):
    """The fetch was cancelled.

    Somebody cancelled it on the page *Downloads*. What was read is kept.

    How data is fetched: :doc:`/explanation/pipeline`.
    """

    title = _("Cancelled")
    guide = "explanation/pipeline.html"
    guide_title = _("How data is fetched")
