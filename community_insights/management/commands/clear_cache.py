from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from community_insights.cleanup import clear_unused
from community_insights.models import Repository


class Command(BaseCommand):
    """manage.py clear_cache: delete what was not used for some days."""

    help = "Delete cached repositories and people that were not used for some days."

    def add_arguments(self, parser):
        """--days and --dry-run.

        Args:
            parser: The parser of the arguments of the command.
        """
        parser.add_argument(
            "--days", type=int, default=30, help="unused for this long (default 30)"
        )
        parser.add_argument("--dry-run", action="store_true", help="only list what would go")

    def handle(self, *args, days, dry_run, **options):
        """List what is old and delete it, unless it is a dry run.

        Args:
            *args: The positional arguments Django passes.
            **options: The other options of the command.
            days: How long unused.
            dry_run: True to list only.
        """
        limit = timezone.now() - timedelta(days=days)
        for repository in Repository.objects.filter(last_used_at__lt=limit).order_by(
            "last_used_at"
        ):
            self.stdout.write(f"{repository.last_used_at:%Y-%m-%d} {repository.full_name}")
        if dry_run:
            return
        repositories, people = clear_unused(days)
        self.stdout.write(f"deleted {repositories} repositories and {people} people")
