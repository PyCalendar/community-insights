import django_filters

from ..models import Item

STATES = [("open", "open"), ("closed", "closed"), ("merged", "merged")]


class ItemFilter(django_filters.FilterSet):
    """The filters of the list of pull requests and issues."""

    kind = django_filters.ChoiceFilter(choices=[(Item.PR, "pull requests"), (Item.ISSUE, "issues")])
    state = django_filters.ChoiceFilter(choices=STATES, method="by_state")
    author = django_filters.CharFilter(lookup_expr="icontains")
    responded = django_filters.BooleanFilter(
        field_name="first_response_at", lookup_expr="isnull", exclude=True, label="Responded"
    )

    class Meta:
        model = Item
        fields = ["kind", "state", "author", "responded"]

    def by_state(self, queryset, name, value):
        """Open, closed, or merged pull requests."""
        if value == "merged":
            return queryset.filter(merged=True)
        return queryset.filter(state=value)
