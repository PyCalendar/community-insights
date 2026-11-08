import django_tables2 as tables
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from ..models import Item
from ..stats import format_duration

STATE_NAMES = {"open": _("open"), "closed": _("closed"), "merged": _("merged")}


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
        fields = ["number", "state", "author", "created_at", "response"]
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
        """merged, open or closed, in the colours of GitHub.

        Args:
            record: The item.

        Returns:
            The state.
        """
        state = "merged" if record.merged else record.state
        return format_html('<span class="badge state-{}">{}</span>', state, STATE_NAMES[state])

    def render_response(self, record, value):
        """The time until the first response, and how long an open item waits.

        Args:
            record: The item, with ``waiting``: open, and no response of a collaborator or
                higher.
            value: The time until its first response, None without one.

        Returns:
            The duration, how long it waits, or that a closed item got no response.
        """
        if not record.waiting:
            if value is None:
                return format_html('<span class="text-muted">{}</span>', _("no response"))
            return format_duration(value.total_seconds())
        waited = format_duration(max((timezone.now() - record.created_at).total_seconds(), 0))
        label = format_html(
            '<span class="badge text-bg-warning">{}</span>',
            _("waiting %(time)s") % {"time": waited},
        )
        if value is None:
            return label
        return format_html("{} {}", format_duration(value.total_seconds()), label)
