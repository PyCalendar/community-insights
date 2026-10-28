from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from community_insights.classify import ensure_default_classes
from community_insights.demo import DEMO, DemoClient
from community_insights.models import Project
from community_insights.sync import read_repository, store_repository


class Command(BaseCommand):
    """manage.py demo_data: a made up project to try the site without GitHub."""

    help = f"Add the made up project {DEMO} to a user, to try the site without GitHub."

    def add_arguments(self, parser):
        """The user who gets the project, admin by default.

        Args:
            parser: The parser of the arguments of the command.
        """
        parser.add_argument("username", nargs="?", default="admin@example.com")

    def handle(self, *args, username, **options):
        """Add the project and read its made up data, once.

        Args:
            *args: The positional arguments Django passes.
            **options: The other options of the command.
            username: Who gets the project.

        Raises:
            CommandError: If there is no such user.
        """
        users = get_user_model().objects
        user = (
            users.filter(username__iexact=username).first()
            or users.filter(email__iexact=username).order_by("pk").first()
        )
        if user is None:
            raise CommandError(f"There is no user {username}.")
        ensure_default_classes(user)
        repository = store_repository(
            {"nameWithOwner": DEMO, "description": "Made up data", "stargazerCount": 42}
        )
        project, created = Project.objects.get_or_create(user=user, target=DEMO)
        project.repositories.add(repository)
        if repository.items.exists():
            self.stdout.write(f"{DEMO} has its data.")
            return
        message = read_repository(DemoClient(), repository)
        self.stdout.write(f"{DEMO} for {username}: {message}")
