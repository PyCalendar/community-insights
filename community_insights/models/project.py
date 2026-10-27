import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone

from .repository import Repository


class Project(models.Model):
    """What a user follows: a repository or an organisation.

    What a user follows: one repository ("owner/name") or all repositories of an organisation or
    user ("owner").
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.CASCADE, related_name="projects")
    target = models.CharField(max_length=200)
    name = models.CharField(max_length=100, blank=True)  # shown instead of the target
    is_private = models.BooleanField(default=False)
    repositories = models.ManyToManyField(Repository, blank=True, related_name="projects")
    badge_token = models.CharField(max_length=40, unique=True, default=secrets.token_urlsafe)
    created = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("user", "target")]
        ordering = ["target"]

    def __str__(self):
        return self.label

    @property
    def label(self) -> str:
        """The name to show: the chosen one, else owner/name or owner."""
        return self.name or self.target

    @property
    def is_owner(self):
        """Whether it is a whole organisation or user, not one repository."""
        return "/" not in self.target
