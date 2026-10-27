from django.core.management.base import BaseCommand

from community_insights import pipeline


class Command(BaseCommand):
    """manage.py fetch_worker: run the queued fetches, for the external modes of FETCH_WORKER."""

    help = "Run the queued fetches from GitHub, highest priority first (FETCH_WORKER=external-...)."

    def add_arguments(self, parser):
        """--once to stop when the queue is empty.

        Args:
            parser: The parser of the arguments of the command.
        """
        parser.add_argument("--once", action="store_true", help="stop when the queue is empty")

    def handle(self, *args, once, **options):
        """Put stale jobs back into the queue and run the queue.

        Args:
            *args: The positional arguments Django passes.
            **options: The other options of the command.
            once: True to stop when the queue is empty.
        """
        pipeline.requeue_stale()
        count = pipeline.work(once=once)
        self.stdout.write(f"{count} jobs run")
