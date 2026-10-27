from django.db import models

from .item import Item


class Event(models.Model):
    """A comment or review on an item by someone, or the opening of the item."""

    OPENED, COMMENT, REVIEW = "opened", "comment", "review"
    KINDS = [(OPENED, "opened"), (COMMENT, "comment"), (REVIEW, "review")]
    item = models.ForeignKey(Item, models.CASCADE, related_name="events")
    actor = models.CharField(max_length=100, db_index=True)
    association = models.CharField(max_length=40, blank=True)
    is_bot = models.BooleanField(default=False)
    kind = models.CharField(max_length=10, choices=KINDS)
    at = models.DateTimeField(db_index=True)

    item_id: int  # the column of the foreign key, for the type checker

    class Meta:
        ordering = ["at"]
