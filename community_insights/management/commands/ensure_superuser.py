import os

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """manage.py ensure_superuser: the superuser of a test site, if missing."""

    help = (
        'Create the superuser of $DEFAULT_SUPERUSER ("name:password") if it is missing. '
        "For test sites: never set it in production."
    )

    def add_arguments(self, parser):
        """name:password, or $DEFAULT_SUPERUSER."""
        parser.add_argument("credentials", nargs="?", help='"name:password", or $DEFAULT_SUPERUSER')

    def handle(self, *args, credentials=None, **options):
        """Create the superuser with a confirmed email address, unless it exists."""
        credentials = credentials or os.environ.get("DEFAULT_SUPERUSER", "")
        if not credentials:
            return
        name, sep, password = credentials.partition(":")
        if not sep or not name or not password:
            raise CommandError('DEFAULT_SUPERUSER must be "name:password"')
        User = get_user_model()
        if User.objects.filter(username=name).exists():
            self.stdout.write(f"The superuser {name} exists.")
            return
        email = f"{name}@example.org"
        user = User.objects.create_superuser(name, email, password)
        # allauth signs in with the email address
        EmailAddress.objects.create(user=user, email=email, verified=True, primary=True)
        self.stdout.write(f"Created the superuser {name} ({email}).")
