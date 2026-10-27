from django.conf import settings
from django.db import models
from django.utils import timezone


class Document(models.Model):
    """A file made in the background, such as an ODS of the statistics, with its progress.

    It belongs to a user, or to the session of a visitor. When it is ready, a user gets a
    message with the link to download it (``Message``).
    """

    QUEUED, RUNNING, DONE, FAILED = "queued", "running", "done", "failed"
    STATUSES = [(QUEUED, "queued"), (RUNNING, "running"), (DONE, "done"), (FAILED, "failed")]
    TABLE, QUERY = "table", "query"  # a table behind the statistics, or a query's result

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, models.CASCADE, related_name="documents", null=True, blank=True
    )
    user_id: int | None  # the column of the foreign key, for the type checker
    session_key = models.CharField(max_length=40, blank=True)  # of a visitor
    kind = models.CharField(max_length=10, default=TABLE)
    table = models.CharField(max_length=30)  # such as responses or contributors
    scope = models.CharField(max_length=500)  # the text of the scope in the address
    parameters = models.JSONField(default=dict, blank=True)  # the query and the time range
    time_zone = models.CharField(max_length=60, default="UTC")  # of the browser, for dates
    language = models.CharField(max_length=10, default="en")  # of the page, for the message
    filename = models.CharField(max_length=200)
    status = models.CharField(max_length=10, choices=STATUSES, default=QUEUED)
    progress = models.PositiveSmallIntegerField(default=0)  # percent
    message = models.TextField(blank=True)  # what went wrong
    error_code = models.CharField(max_length=60, blank=True)
    created = models.DateTimeField(default=timezone.now)
    finished = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return self.filename

    def path(self):
        """Where the file is stored.

        Returns:
            The path in ``DATA_DIR/documents``.
        """
        return settings.DATA_DIR / "documents" / f"{self.pk}-{self.filename}"

    def owned_by(self, request) -> bool:
        """Whether the person of a request may see the document.

        Args:
            request: The request.

        Returns:
            True for its user, or for the visitor of its session.
        """
        if self.user_id is not None:
            return request.user.is_authenticated and request.user.pk == self.user_id
        key = request.session.session_key
        return bool(key) and key == self.session_key
