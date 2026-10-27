from django.conf import settings
from django.db import models
from django.utils import timezone


class SavedQuery(models.Model):
    """A query of the contributors page, to run it again."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.CASCADE, related_name="queries")
    name = models.CharField(max_length=100)
    where = models.TextField(blank=True)
    sort = models.CharField(max_length=60, blank=True)
    columns = models.CharField(max_length=500, blank=True)
    group = models.CharField(max_length=20, blank=True)
    chart = models.CharField(max_length=30, blank=True)
    created = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["name"]
        unique_together = [("user", "name")]

    def __str__(self):
        return self.name

    def parameters(self) -> str:
        """The query as the parameters of an address of the contributors page."""
        from urllib.parse import urlencode

        return urlencode(
            {
                "where": self.where,
                "sort": self.sort,
                "columns": self.columns,
                "group": self.group,
                "chart": self.chart,
            }
        )
