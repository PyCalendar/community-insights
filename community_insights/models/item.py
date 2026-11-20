from typing import TYPE_CHECKING

from django.db import models

from .repository import Repository

if TYPE_CHECKING:
    from django.db.models.manager import RelatedManager

    from .event import Event
    from .item_commit import ItemCommit


class Item(models.Model):
    """A pull request or an issue."""

    PR, ISSUE = "pr", "issue"
    # the version of the details that the pages Replies and Reviews need: 2 with whether it
    # is a draft and the kind of each review
    DETAILS = 2
    repository = models.ForeignKey(Repository, models.CASCADE, related_name="items")
    kind = models.CharField(max_length=5, choices=[(PR, "pull request"), (ISSUE, "issue")])
    number = models.IntegerField()
    node_id = models.CharField(max_length=100, blank=True)
    title = models.CharField(max_length=500, blank=True)
    author = models.CharField(max_length=100, blank=True, db_index=True)
    author_association = models.CharField(max_length=40, blank=True)
    author_is_bot = models.BooleanField(default=False)
    state = models.CharField(max_length=10)  # open, closed
    merged = models.BooleanField(default=False)
    # a pull request marked as a draft on GitHub: not ready for review; open drafts do not
    # count as open pull requests unless the page says so (``drafts=1``)
    draft = models.BooleanField(default=False)
    created_at = models.DateTimeField(db_index=True)
    updated_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True, blank=True)
    merged_by = models.CharField(max_length=100, blank=True)
    closed_by = models.CharField(max_length=100, blank=True)
    # what of the details was read: 0 nothing, 1 the last commits, the closer and the
    # approvals, 2 also whether it is a draft and the kind of each review (DETAILS)
    details = models.PositiveSmallIntegerField(default=0)

    if TYPE_CHECKING:  # the reverse relation, for the type checker
        events: RelatedManager[Event]
        commits: RelatedManager[ItemCommit]

    class Meta:
        unique_together = [("repository", "kind", "number")]
        indexes = [models.Index(fields=["repository", "kind", "created_at"])]

    def __str__(self):
        return f"{self.repository.full_name}#{self.number}"
