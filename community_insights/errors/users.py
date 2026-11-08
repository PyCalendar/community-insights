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


class UnknownEmailAddress(UserAdministrationError):
    """No account has this email address.

    ``manage.py make_admin`` makes the account with this email address an administrator.
    Check the address for typing errors, or let the person sign up first.

    How to manage the users: :doc:`/how-to/users`.
    """

    title = _("No account with this email address")
    guide = "how-to/users.html#from-the-command-line"
    guide_title = _("How to manage the users")


class EmailAddressNotConfirmed(UserAdministrationError):
    """The email address of the account is not confirmed.

    Only an account whose email address is confirmed becomes an administrator from the
    command line, so that nobody becomes one with an address that is not theirs. Ask the
    person to confirm it with the link of the confirmation mail, or send the mail again on
    their page *Profile*, then run the command again.

    How to manage the users: :doc:`/how-to/users`.
    """

    title = _("Email address not confirmed")
    guide = "how-to/users.html#from-the-command-line"
    guide_title = _("How to manage the users")
