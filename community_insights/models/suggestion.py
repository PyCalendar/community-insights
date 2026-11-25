from django.db import models

from .item import Item


class Suggestion(models.Model):
    """A review comment of a pull request that suggests code, and whether it was applied.

    Read with the review threads of the pull request (``sync.suggestions``); the status is
    decided then, and read again when the pull request changes.
    """

    APPLIED, OPEN, UNKNOWN = "applied", "open", "unknown"
    STATUSES = [(APPLIED, "applied"), (OPEN, "open"), (UNKNOWN, "unknown")]

    item = models.ForeignKey(Item, models.CASCADE, related_name="suggestions")
    comment_id = models.BigIntegerField()
    url = models.URLField(max_length=500, blank=True)
    author = models.CharField(max_length=100, blank=True, db_index=True)  # the suggester
    created_at = models.DateTimeField()
    path = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=10, choices=STATUSES)
    # why: commit-suggestion, commit-named, resolved-by-suggester, resolved-by-other,
    # answered-with-suggestion, or "" for an open one
    reason = models.CharField(max_length=30, blank=True)
    resolved = models.BooleanField(default=False)
    resolved_by = models.CharField(max_length=100, blank=True)
    # of the author of the pull request and the suggester, who wrote last in the thread
    last_by = models.CharField(max_length=100, blank=True)
    last_role = models.CharField(max_length=10, blank=True)  # author or suggester
    last_at = models.DateTimeField(null=True, blank=True)
    last_url = models.URLField(max_length=500, blank=True)

    item_id: int  # the column of the foreign key, for the type checker

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["item", "comment_id"], name="one_suggestion_per_comment"
            )
        ]

    def __str__(self):
        return f"{self.item} {self.comment_id} {self.status}"
