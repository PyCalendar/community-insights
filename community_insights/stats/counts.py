from datetime import datetime

from django.db.models import Count, Q

from ..models import Item
from .selection import items_in


def counts(repositories, since: datetime | None = None, until: datetime | None = None) -> dict:
    """Pull requests and issues created in the time range, by state.

    Args:
        repositories: The repositories.
        since: The start of the time range, None for the beginning.
        until: The end of the time range, excluded; None for now.

    Returns:
        For pull requests and issues: total, open, merged and closed.
    """
    items = items_in(repositories, since, until)
    prs = items.filter(kind=Item.PR).aggregate(
        n_total=Count("id"),
        n_open=Count("id", filter=Q(state="open")),
        n_merged=Count("id", filter=Q(merged=True)),
        n_closed=Count("id", filter=Q(state="closed", merged=False)),
    )
    issues = items.filter(kind=Item.ISSUE).aggregate(
        n_total=Count("id"),
        n_open=Count("id", filter=Q(state="open")),
        n_closed=Count("id", filter=Q(state="closed")),
    )
    return {
        "prs": {k.removeprefix("n_"): v for k, v in prs.items()},
        "issues": {k.removeprefix("n_"): v for k, v in issues.items()},
    }
