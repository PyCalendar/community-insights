from django.db import models

from .item import Item


class ItemCommit(models.Model):
    """A commit of a pull request: who made it and when, to see answers to feedback.

    Only the last commits of each pull request are read (``sync.queries.COMMITS``): they show
    whether the author changed the pull request after a comment or review. A pull request
    without stored commits was read before commits were read.
    """

    item = models.ForeignKey(Item, models.CASCADE, related_name="commits")
    actor = models.CharField(max_length=100, blank=True)  # the login, "" if GitHub knows none
    at = models.DateTimeField()

    item_id: int  # the column of the foreign key, for the type checker

    class Meta:
        ordering = ["at"]
