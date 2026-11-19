from django.core.management.base import BaseCommand, CommandError

from community_insights.models import Repository
from community_insights.sync import store


class Command(BaseCommand):
    """manage.py locate: find the places of the locations of the people of repositories."""

    help = (
        "Find the places of the new locations of the people of repositories (GeoNames, then "
        "Nominatim). The fetch worker runs it in a process of its own: GeoNames needs 100 MB."
    )

    def add_arguments(self, parser):
        """The numbers of the repositories, all without one.

        Args:
            parser: The parser of the arguments of the command.
        """
        parser.add_argument("repositories", nargs="*", type=int, help="numbers of repositories")

    def handle(self, *args, repositories, **options):
        """Locate the people of each repository.

        Args:
            *args: The positional arguments Django passes.
            repositories: The numbers of the repositories; all without one.
            **options: The other options of the command.

        Raises:
            CommandError: If a repository does not exist.
        """
        from community_insights.locations.locator import Locator

        found = Repository.objects.all()
        if repositories:
            found = found.filter(pk__in=repositories)
            if found.count() != len(set(repositories)):
                raise CommandError(f"no repository with one of the numbers {repositories}")
        locator = Locator.from_settings()  # one budget of Nominatim for all
        for repository in found:
            count = store.locate_here(repository, locator)
            self.stdout.write(f"{repository}: {count} locations known")
