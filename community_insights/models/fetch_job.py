from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .repository import Repository


class FetchJob(models.Model):
    """Reading one repository from GitHub, as a job of the queue.

    Reading one repository from GitHub: queued, then run by the worker in the order of priority
    (highest first), which also decides who gets the tokens.
    """

    QUEUED, RUNNING, DONE, FAILED, CANCELLED, LIMIT = (
        "queued",
        "running",
        "done",
        "failed",
        "cancelled",
        "limit",
    )
    STATUSES = [
        (QUEUED, _("queued")),
        (RUNNING, _("running")),
        (DONE, _("done")),
        (FAILED, _("failed")),
        (CANCELLED, _("cancelled")),
        (LIMIT, _("limit reached")),
    ]
    ACTIVE = (QUEUED, RUNNING)
    LOW, NORMAL, HIGH = -10, 0, 10
    PRIORITIES = [(HIGH, _("high")), (NORMAL, _("normal")), (LOW, _("low"))]

    # None: started by a visitor, with the tokens donated to the site
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, models.CASCADE, related_name="fetch_jobs", null=True, blank=True
    )
    repository = models.ForeignKey(Repository, models.CASCADE, related_name="fetch_jobs")
    status = models.CharField(max_length=10, choices=STATUSES, default=QUEUED, db_index=True)
    priority = models.IntegerField(choices=PRIORITIES, default=NORMAL)
    reason = models.CharField(max_length=300, blank=True)  # e.g. the page it was started from
    reason_url = models.CharField(max_length=300, blank=True)
    point_limit = models.PositiveIntegerField(null=True, blank=True)
    points_estimated = models.PositiveIntegerField(default=0)
    points_used = models.PositiveIntegerField(default=0)
    items_expected = models.PositiveIntegerField(default=0)
    items_done = models.PositiveIntegerField(default=0)
    not_before = models.DateTimeField(null=True, blank=True)  # waiting for a rate limit reset
    cancel_requested = models.BooleanField(default=False)
    created = models.DateTimeField(default=timezone.now)
    started = models.DateTimeField(null=True, blank=True)
    finished = models.DateTimeField(null=True, blank=True)
    message = models.TextField(blank=True)
    error_code = models.CharField(max_length=60, blank=True)  # a class of errors.py

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"{self.repository} ({self.status})"

    @property
    def percent(self) -> int:
        """How far it is, 0 to 100; 100 only when done."""
        if self.status == self.DONE:
            return 100
        if not self.items_expected:
            return 0
        return min(99, round(100 * self.items_done / self.items_expected))
