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
    user_id: int  # the column of the foreign key, for the type checker
    name = models.CharField(max_length=60)
    color = models.CharField(max_length=7, default="#649568")
    # the key of a class the site made (classify.DEFAULT_CLASSES): it is hidden, not deleted
    preset = models.CharField(max_length=30, blank=True)
    # hidden classes still decide who belongs to them, but are not shown in the statistics
    hidden = models.BooleanField(default=False)

    order_with_respect_to = "user"

    if TYPE_CHECKING:  # the reverse relation, for the type checker
        rules: RelatedManager[ClassRule]

    class Meta(OrderedModel.Meta):
        unique_together = [("user", "name")]
        verbose_name_plural = "person classes"

    def __str__(self):
        return self.name

    @property
    def ident(self) -> str:
        """The id of the class in addresses: its name and its number, such as ``maintainer-3``.

        The number makes it unique and finds it again after the class was renamed.
        """
        from django.utils.text import slugify

        return f"{slugify(self.name) or 'class'}-{self.pk}"
