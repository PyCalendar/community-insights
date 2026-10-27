from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models
from ordered_model.models import OrderedModel

if TYPE_CHECKING:
    from django.db.models.manager import RelatedManager

    from .class_rule import ClassRule


class PersonClass(OrderedModel):
    """A class of people for response times, such as "maintainers".

    An actor belongs to the first class in their order (django-ordered-model) with a rule that
    matches.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.CASCADE, related_name="classes")
    name = models.CharField(max_length=60)
    color = models.CharField(max_length=7, default="#649568")

    order_with_respect_to = "user"

    if TYPE_CHECKING:  # the reverse relation, for the type checker
        rules: RelatedManager[ClassRule]

    class Meta(OrderedModel.Meta):
        unique_together = [("user", "name")]
        verbose_name_plural = "person classes"

    def __str__(self):
        return self.name
