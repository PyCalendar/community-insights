from django.db import models
from django.utils.translation import gettext_lazy as _

from .person_class import PersonClass


class ClassRule(models.Model):
    """A rule of a class of people: who belongs to it (see classify.rule_matches)."""

    HANDLE, PATTERN, ASSOCIATION, BOT, LOCATION, ANY = (
        "handle",
        "pattern",
        "association",
        "bot",
        "location",
        "any",
    )
    KINDS = [
        (HANDLE, _("handles (space separated names)")),
        (PATTERN, _("handle pattern (* and ?)")),
        (ASSOCIATION, _("status (owner, member, collaborator, contributor, ...)")),
        (BOT, _("is a bot")),
        (LOCATION, _("location pattern (* and ?)")),
        (ANY, _("everybody")),
    ]
    person_class = models.ForeignKey(PersonClass, models.CASCADE, related_name="rules")
    kind = models.CharField(max_length=12, choices=KINDS)
    value = models.CharField(max_length=500, blank=True)

    def __str__(self):
        return f"{self.kind} {self.value}".strip()
