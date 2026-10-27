from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from community_insights import pipeline
from community_insights.models import FetchJob, Repository


class Command(BaseCommand):
    """manage.py sync: queue and run the fetches of a user's projects, e.g. from cron."""

    help = "Queue and run fetches for a user's projects, e.g. from cron."

    def add_arguments(self, parser):
        """The email of the user, repositories and a limit of points."""
        parser.add_argument("email")
        parser.add_argument("repositories", nargs="*", help="owner/name; all projects if empty")
        parser.add_argument("--limit", type=int, help="API points for this fetch")

    def handle(self, *args, email, repositories, limit, **options):
        """Estimate, queue with low priority, run, and print the outcome of each job."""
        user = get_user_model().objects.filter(email__iexact=email).first()
        if user is None:
            raise CommandError(f"No user {email}")
        selected = Repository.objects.filter(projects__user=user).distinct()
        if repositories:
            selected = selected.filter(full_name__in=repositories)
        estimates, _, _ = pipeline.estimate_for(user, selected)
        jobs = pipeline.enqueue(
            user, estimates, point_limit=limit, reason="manage.py sync", priority=FetchJob.LOW
        )
        pipeline.work(once=True)
        for job in jobs:
            job.refresh_from_db()
            self.stdout.write(f"{job.repository}: {job.status} {job.message}")
