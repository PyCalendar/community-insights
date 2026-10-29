from django.core.management import call_command
from django.core.management.base import BaseCommand

# what the container does before it serves, in this order
STEPS = (
    ("migrate", {"interactive": False}),
    ("invalidate_cachalot", {"verbosity": 0}),  # the cache of the statistics starts fresh
    ("ensure_superuser", {}),  # DEFAULT_SUPERUSER, email:password, each start
    ("check_production", {}),  # stops the container if a default password is used
)


class Command(BaseCommand):
    """manage.py prepare: the steps before the container serves, in one process.

    Each ``manage.py`` loads Django and the libraries of the statistics, which takes
    seconds; one process for all steps lets the site answer the health check sooner.
    """

    help = "Migrate, empty the cache of the statistics, create the superuser and check it."

    def handle(self, *args, **options):
        """Run the steps one after the other; the first error stops them.

        Args:
            *args: The positional arguments Django passes.
            **options: The other options of the command.
        """
        for name, step_options in STEPS:
            call_command(name, stdout=self.stdout, stderr=self.stderr, **step_options)
