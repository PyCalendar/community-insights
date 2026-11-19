from django.db import models
from django.utils import timezone


class Location(models.Model):
    """Where a location of GitHub profiles is, found once for each text.

    The text is the location as written; a person who changes theirs gets a new one, which is
    found again. What was not found is kept too (an empty country), so it is not asked again.
    """

    GEONAMES, NOMINATIM = "geonames", "nominatim"

    text = models.CharField(max_length=200, unique=True)
    country = models.CharField(max_length=2, blank=True)
    region = models.CharField(max_length=10, blank=True)
    city = models.CharField(max_length=200, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    source = models.CharField(max_length=20, blank=True)
    found_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["text"]

    def __str__(self):
        return f"{self.text} ({self.country or '?'})"
