from django.db import models

from .repository import Repository


class Commit(models.Model):
    """A commit of the default branch of a repository."""

    repository = models.ForeignKey(Repository, models.CASCADE, related_name="commits")
    sha = models.CharField(max_length=40)
    author = models.CharField(max_length=100, blank=True, db_index=True)  # login, if known
    author_name = models.CharField(max_length=200, blank=True)
    at = models.DateTimeField(db_index=True)

    class Meta:
        unique_together = [("repository", "sha")]
        ordering = ["-at"]

    def __str__(self):
        return f"{self.repository}@{self.sha[:7]}"
