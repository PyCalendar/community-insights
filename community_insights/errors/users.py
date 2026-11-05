"""Errors of the page Users, where administrators manage the accounts of the site."""

from django.utils.translation import gettext_lazy as _

from .base import CommunityError


class UserAdministrationError(CommunityError):
    """A change on the page *Users* was not made.

    The message says why. Only the subclasses are raised.

    How to manage the users: :doc:`/how-to/users`.
    """

    title = _("User not changed")
    guide = "how-to/users.html"
    guide_title = _("How to manage the users")


class CannotRemoveOwnAdminAccess(UserAdministrationError):
    """Administrators cannot remove their own administrator access.

    Otherwise the site could be left without an administrator. Ask another
    administrator to remove your access, or make somebody else an
    administrator first and let them do it.

    How to manage the users: :doc:`/how-to/users`.
    """

    title = _("Your own administrator access stays")
    guide = "how-to/users.html"
    guide_title = _("How to manage the users")
