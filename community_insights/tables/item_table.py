import django_tables2 as tables
from django.utils import timezone
from django.utils.html import format_html

from ..models import Item
from ..stats import format_duration


class ItemTable(tables.Table):
    """Pull requests and issues with their first response; the columns sort."""

    number = tables.Column(verbose_name="Item", order_by=("repository__full_name", "number"))
    author = tables.Column(empty_values=(), default="-")
    created_at = tables.DateColumn(verbose_name="Created", format="Y-m-d")
    state = tables.Column(order_by=("merged", "state"))
    response = tables.Column(
        verbose_name="First response", empty_values=(), attrs={"td": {"class": "text-end"}}
    )

    class Meta:
        model = Item
        fields = ["number", "author", "created_at", "state", "response"]
        order_by = "-created_at"
        attrs = {"class": "table table-sm table-hover align-middle"}

    def render_number(self, record):
        """owner/name#number, linked to GitHub, with its kind.

        Args:
            record: The item.

        Returns:
            The link and the badge of its kind.
        """
        path = "pull" if record.kind == Item.PR else "issues"
        label = "PR" if record.kind == Item.PR else "issue"
        return format_html(
            '<a href="https://github.com/{0}/{1}/{2}">{0}#{2}</a> '
            '<span class="badge text-bg-secondary">{3}</span>',
            record.repository.full_name,
            path,
            record.number,
            label,
        )

    def render_state(self, record):
        """merged, open or closed.

        Args:
            record: The item.

        Returns:
            The state.
        """
        return "merged" if record.merged else record.state

    def render_response(self, record, value):
        """The time until the first response, or how long it waits.

        Args:
            record: The item.
            value: The time until its first response, None without one.

        Returns:
            The duration, or how long it waits.
        """
        if value is not None:
            return format_duration(value.total_seconds())
        end = record.closed_at or timezone.now()
        waited = format_duration(max((end - record.created_at).total_seconds(), 0))
        return format_html('<span class="text-muted">waiting {}</span>', waited)
