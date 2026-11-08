from allauth.account.models import EmailAddress
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext

from community_insights.errors import EmailAddressNotConfirmed, UnknownEmailAddress


def make_admin(email: str):
    """Make the account with a confirmed email address an administrator.

    Args:
        email: The email address, in any case.

    Returns:
        The user, now staff and superuser.

    Raises:
        UnknownEmailAddress: If no account has this address.
        EmailAddressNotConfirmed: If the address of the account is not confirmed.
    """
    found = EmailAddress.objects.filter(email__iexact=email.strip()).select_related("user")
    if not found.exists():
        raise UnknownEmailAddress(
            gettext("No account has the email address %(email)s.") % {"email": email}
        )
    confirmed = found.filter(verified=True).first()
    if confirmed is None:
        raise EmailAddressNotConfirmed(
            gettext("%(email)s is not confirmed: the person confirms it first.") % {"email": email}
        )
    user = confirmed.user
    user.is_staff = user.is_superuser = True
    user.save(update_fields=["is_staff", "is_superuser"])
    return user


class Command(BaseCommand):
    """manage.py make_admin EMAIL: make the account with this confirmed address an administrator."""

    help = "Make the account with this confirmed email address an administrator."

    def add_arguments(self, parser):
        """The email address.

        Args:
            parser: The parser of the arguments of the command.
        """
        parser.add_argument("email", help="the confirmed email address of the account")

    def handle(self, *args, email, **options):
        """Make the account an administrator, or say why not.

        Args:
            *args: The positional arguments Django passes.
            email: The email address.
            **options: The other options of the command.

        Raises:
            CommandError: If no account has the address or it is not confirmed.
        """
        try:
            user = make_admin(email)
        except (UnknownEmailAddress, EmailAddressNotConfirmed) as error:
            raise CommandError(f"{error.title}: {error}") from error
        self.stdout.write(f"{user.email or email} is an administrator now.")
