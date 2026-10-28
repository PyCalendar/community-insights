from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

# passwords that are tried first: never on a site others can reach
DEFAULT_PASSWORDS = ("admin", "password", "123456", "12345678", "changeme", "secret", "root")


def weak_password_users() -> list[str]:
    """The superusers whose password is a default one, their own name or email address.

    Returns:
        Their usernames.
    """
    found = []
    for user in get_user_model().objects.filter(is_superuser=True):
        own = (user.username, user.username.split("@")[0], user.email, user.email.split("@")[0])
        if any(user.check_password(p) for p in (*DEFAULT_PASSWORDS, *own) if p):
            found.append(user.username)
    return found


class Command(BaseCommand):
    """manage.py check_production: refuse to run a production site with default passwords."""

    help = "Stop with an error if PRODUCTION is on and a superuser has a default password."

    def handle(self, *args, **options):
        """Check the superusers when PRODUCTION is on.

        Args:
            *args: The positional arguments Django passes.
            **options: The other options of the command.

        Raises:
            CommandError: If a superuser has a default password in production.
        """
        if not settings.PRODUCTION:
            self.stdout.write("PRODUCTION=false: the passwords are not checked.")
            return
        weak = weak_password_users()
        if weak:
            raise CommandError(
                f"The superuser {', '.join(weak)} has a default password, and PRODUCTION is on. "
                "Change it: python manage.py changepassword NAME, or sign in and use "
                "/accounts/password/change/. Remove DEFAULT_SUPERUSER. For a local test "
                "site, set PRODUCTION=false."
            )
        self.stdout.write("No superuser has a default password.")
