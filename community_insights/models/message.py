from django.conf import settings
from django.db import models
from django.utils import timezone


class Message(models.Model):
    """A message to a user, such as that a document is ready, read or not yet."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.CASCADE, related_name="messages")
    title = models.CharField(max_length=200)
    text = models.TextField(blank=True)
    link = models.CharField(max_length=500, blank=True)  # an address of this site
    created = models.DateTimeField(default=timezone.now)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return self.title

    @property
    def unread(self) -> bool:
        """Whether the user has not opened it yet."""
        return self.read_at is None

    def mark_read(self) -> None:
        """Remember that the user opened it, once."""
        if self.read_at is None:
            self.read_at = timezone.now()
            self.save(update_fields=["read_at"])
