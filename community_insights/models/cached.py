from django.db import models
from django.utils import timezone


class Cached(models.Model):
    """Data read from GitHub, with when it was read and last used.

    Data read from GitHub: when it was created, read and last used, so what nobody uses can be
    deleted.
    """

    created = models.DateTimeField(default=timezone.now)
    fetched_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        abstract = True

    def touch(self):
        """Remember that this object was used."""
        type(self).objects.filter(pk=self.pk).update(last_used_at=timezone.now())
