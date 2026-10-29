from datetime import timedelta

from django.db import models
from django.utils import timezone

# Each write of a table makes django-cachalot forget its answers and moves the stamp of the
# data (data_stamp.py); the clean-up counts in days, so an hour is exact enough.
TOUCH_EVERY = timedelta(hours=1)


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
        """Remember that this object was used, at most once an hour."""
        type(self).touch_all(type(self).objects.filter(pk=self.pk))

    @staticmethod
    def touch_all(objects) -> int:
        """Remember that the objects were used, writing only those not used for an hour.

        Args:
            objects: A query of objects of a subclass, such as repositories.

        Returns:
            How many were written; 0 without writing to the table.
        """
        now = timezone.now()
        stale = objects.filter(last_used_at__lt=now - TOUCH_EVERY)
        if not stale.exists():  # a read, answered by cachalot: the table stays unchanged
            return 0
        return stale.update(last_used_at=now)
