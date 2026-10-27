from django.db import models

from .cached import Cached


class Person(Cached):
    """Somebody on GitHub: name, location and avatar, read again after some time."""

    login = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=200, blank=True)
    avatar_url = models.URLField(blank=True)
    is_bot = models.BooleanField(default=False)

    class Meta(Cached.Meta):
        verbose_name_plural = "people"
        ordering = ["login"]

    def __str__(self):
        return self.login
