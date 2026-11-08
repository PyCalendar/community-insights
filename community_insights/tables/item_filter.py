import django_filters
from django import forms
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from ..models import Item

KINDS = [(Item.PR, _("pull requests")), (Item.ISSUE, _("issues"))]
STATES = [("open", _("open")), ("closed", _("closed")), ("merged", _("merged"))]
RESPONDED = [("true", _("yes")), ("false", _("no"))]  # the values of the addresses before


class ItemFilter(django_filters.FilterSet):
    """The filters of the list of pull requests and issues.

    Kind, state and response are multiple choices: all are chosen when an address names none,
    such as ``?state=closed&state=merged``.
    """

    kind = django_filters.MultipleChoiceFilter(
        choices=KINDS, widget=forms.CheckboxSelectMultiple, label=_("Kind")
    )
    state = django_filters.MultipleChoiceFilter(
        choices=STATES, method="by_state", widget=forms.CheckboxSelectMultiple, label=_("State")
    )
    author = django_filters.CharFilter(lookup_expr="icontains", label=_("Author"))
    responded = django_filters.MultipleChoiceFilter(
        choices=RESPONDED,
        method="by_response",
        widget=forms.CheckboxSelectMultiple,
        label=_("Responded"),
    )

    class Meta:
        model = Item
        fields = ["kind", "state", "author", "responded"]

    def __init__(self, data=None, *args, **kwargs):
        """The filters of the address; a multiple choice it does not name has all chosen.

        Args:
            data: The parameters of the address.
            *args: The arguments of django-filter.
            **kwargs: Its keyword arguments.
        """
        data = data.copy() if data is not None else None
        if data is not None:
            for name, choices in (("kind", KINDS), ("state", STATES), ("responded", RESPONDED)):
                if not [value for value in data.getlist(name) if value]:
                    data.setlist(name, [value for value, _label in choices])
        super().__init__(data, *args, **kwargs)

    def by_state(self, queryset, name, value):
        """Open ones, those closed without merging, merged ones, or several of them.

        Args:
            queryset: The items.
            name: The name of the filter.
            value: Some of ``open``, ``closed`` and ``merged``.

        Returns:
            The items in one of these states.
        """
        wanted = Q(pk__in=[])
        if "open" in value:
            wanted |= Q(state="open")
        if "closed" in value:
            wanted |= Q(state="closed", merged=False)
        if "merged" in value:
            wanted |= Q(merged=True)
        return queryset.filter(wanted)

    def by_response(self, queryset, name, value):
        """Leave the items as they are: the responses are found after the query, see ``keep``.

        Args:
            queryset: The items.
            name: The name of the filter.
            value: Some of ``true`` and ``false``.

        Returns:
            The items, unchanged.
        """
        return queryset

    def keep(self, rows: list) -> list:
        """The items with a first response, those without, or both, as chosen.

        Args:
            rows: The items of ``items_with_responses``, with ``first_response_at``.

        Returns:
            The items chosen.
        """
        chosen = set(self.form.cleaned_data.get("responded") or []) if self.is_valid() else set()
        return [
            row
            for row in rows
            if ("true" if row.first_response_at is not None else "false") in chosen
        ]
