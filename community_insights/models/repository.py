from typing import TYPE_CHECKING

from django.db import models

from .cached import Cached

if TYPE_CHECKING:
    from django.db.models.manager import RelatedManager

    from .commit import Commit
    from .item import Item


class Repository(Cached):
    """A repository on GitHub with what was read of it and up to when."""

    full_name = models.CharField(max_length=200, unique=True)
    owner_login = models.CharField(max_length=100, db_index=True)
    description = models.TextField(blank=True)
    stars = models.IntegerField(default=0)
    is_private = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    # how many there are on GitHub, from the last estimate or fetch
    prs_total = models.PositiveIntegerField(null=True, blank=True)
    totals_checked_at = models.DateTimeField(null=True, blank=True)
    # where a stopped fetch continues, per kind: {"pr": {"cursor", "stop", "newest"}}
    resume = models.JSONField(default=dict, blank=True)
    issues_total = models.PositiveIntegerField(null=True, blank=True)
    # the newest `updated_at` of pull requests / issues read: later syncs start there
    prs_synced_until = models.DateTimeField(null=True, blank=True)
    issues_synced_until = models.DateTimeField(null=True, blank=True)
    commits_synced_until = models.DateTimeField(null=True, blank=True)
    commits_total = models.PositiveIntegerField(null=True, blank=True)

    if TYPE_CHECKING:  # the reverse relations, for the type checker
        items: RelatedManager[Item]
        commits: RelatedManager[Commit]

    class Meta(Cached.Meta):
        verbose_name_plural = "repositories"
        ordering = ["-stars", "full_name"]

    def __str__(self):
        return self.full_name

    @property
    def url(self):
        """The address of the repository on GitHub."""
        return f"https://github.com/{self.full_name}"
