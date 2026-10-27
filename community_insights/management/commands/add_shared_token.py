from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from community_insights.models import AccessToken
from community_insights.tokens import ask_one


class Command(BaseCommand):
    """manage.py add_shared_token: a GitHub token everyone on this site can use."""

    help = (
        "Add a GitHub token that everybody on this site can use, owned by a superuser "
        "who must exist. The token is checked with GitHub."
    )

    def add_arguments(self, parser):
        """The superuser, the token and how much of it may be used.

        Args:
            parser: The parser of the arguments of the command.
        """
        parser.add_argument("superuser", help="the username of the superuser who owns it")
        parser.add_argument("token", help="the GitHub token, best with an expiration date")
        parser.add_argument("--label", default="shared by the site")
        parser.add_argument(
            "--max-percent", type=int, default=100, help="points per hour the site may use"
        )

    def handle(self, *args, superuser, token, label, max_percent, **options):
        """Check the token with GitHub and store it, fully shared.

        Args:
            *args: The positional arguments Django passes.
            **options: The other options of the command.
            superuser: The username of the superuser who owns the token.
            token: The token.
            label: The name of the token.
            max_percent: The share of its points per hour the site may use.

        Raises:
            CommandError: If the superuser does not exist or the token does not work.
        """
        owner = get_user_model().objects.filter(username=superuser).first()
        if owner is None:
            raise CommandError(f"There is no user {superuser!r}: create the superuser first.")
        if not owner.is_superuser:
            raise CommandError(f"{superuser!r} is no superuser.")
        if not 0 <= max_percent <= 100:
            raise CommandError("--max-percent is between 0 and 100.")
        try:
            login, client = ask_one(token, "viewer")
        except Exception as error:  # shown to who runs the command
            raise CommandError(f"GitHub does not accept the token: {error}") from error
        stored = AccessToken.objects.create(
            user=owner,
            token=token,
            login=login,
            label=label[:100],
            max_percent=max_percent,
            shared_percent=100,
            expires_at=client.rate.expires_at,
            rate_limit=client.rate.limit,
            rate_remaining=client.rate.remaining,
            rate_reset_at=client.rate.reset_at,
        )
        self.stdout.write(
            f"The token of {login} is shared: {stored.shared_points} points per hour "
            f"for everybody, owned by {superuser}."
        )
        if client.rate.expires_at is None:
            self.stdout.write("It never expires: some organisations, such as Plone, refuse it.")
