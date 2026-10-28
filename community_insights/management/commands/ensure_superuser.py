import os

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import transaction
from django.utils.translation import gettext

from community_insights.errors import InvalidDefaultSuperuser


def parse(credentials: str) -> tuple[str, str]:
    """The email address and the password of ``email:password``.

    Args:
        credentials: The text, such as ``admin@example.com:a-long-password``.

    Returns:
        The email address in lower case, and the password, which may contain ``:``.

    Raises:
        InvalidDefaultSuperuser: If there is no password or no valid email address.

    Examples:
        >>> parse("Admin@Example.com:pass:word")
        ('admin@example.com', 'pass:word')
    """
    email, separator, password = credentials.strip().partition(":")
    email = email.strip().lower()
    try:
        validate_email(email)
    except ValidationError as error:
        raise InvalidDefaultSuperuser(
            gettext('DEFAULT_SUPERUSER must be "email:password"; %(email)s is no email address.')
            % {"email": repr(email)}
        ) from error
    if not separator or not password:
        raise InvalidDefaultSuperuser(
            gettext('DEFAULT_SUPERUSER must be "email:password"; the password is missing.')
        )
    return email, password


class Command(BaseCommand):
    """manage.py ensure_superuser: the superuser of $DEFAULT_SUPERUSER, at each start."""

    help = (
        'Create or update the superuser of $DEFAULT_SUPERUSER ("email:password"): it signs in '
        "with the email address, and the password is set each time. Nothing without it."
    )

    def add_arguments(self, parser):
        """email:password, or $DEFAULT_SUPERUSER.

        Args:
            parser: The parser of the arguments of the command.
        """
        parser.add_argument(
            "credentials", nargs="?", help='"email:password", or $DEFAULT_SUPERUSER'
        )

    @transaction.atomic
    def handle(self, *args, credentials=None, **options):
        """Create the superuser, or give the existing one the password and the rights.

        Args:
            *args: The positional arguments Django passes.
            **options: The other options of the command.
            credentials: ``email:password``, or None for ``$DEFAULT_SUPERUSER``.

        Raises:
            CommandError: If the credentials are not ``email:password``.
        """
        credentials = credentials or os.environ.get("DEFAULT_SUPERUSER", "")
        if not credentials.strip():
            return
        try:
            email, password = parse(credentials)
        except InvalidDefaultSuperuser as error:
            raise CommandError(f"{error.title}: {error} {error.docs_url()}") from error
        User = get_user_model()
        user = (
            User.objects.filter(email__iexact=email).order_by("pk").first()
            or User.objects.filter(username__iexact=email).first()
        )
        created = user is None
        if user is None:
            user = User.objects.create_superuser(email, email, password)
        else:
            user.is_superuser = user.is_staff = user.is_active = True
            user.set_password(password)
            user.save()
        # allauth signs in with the email address: a verified, primary one
        EmailAddress.objects.filter(user=user).exclude(email__iexact=email).update(primary=False)
        EmailAddress.objects.update_or_create(
            user=user, email=email, defaults={"verified": True, "primary": True}
        )
        self.stdout.write(f"{'Created' if created else 'Updated'} the superuser {email}.")
