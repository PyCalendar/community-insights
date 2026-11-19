"""Pull requests or issues per day, week or month: for the charts of the page Trends."""

from datetime import datetime, tzinfo

from django.db.models import Min

from ..models import Item
from .kind_trend import contribution_events, first_contributions, in_range
from .periods import buckets, count_by, label, size_of

# the numbers per bar, by their keys in what kind_series returns
SERIES = ("opened", "closed", "contributions", "newcomers")


def kind_series(
    repositories,
    kind: str,
    since: datetime | None,
    until: datetime | None,
    now: datetime,
    tz: tzinfo,
) -> dict:
    """Opened, closed, contributions and new contributors per day, week or month.

    For pull requests or for issues, in each day, week or month of the time range.

    Args:
        repositories: The repositories.
        kind: ``pr`` or ``issue``.
        since: The start of the time range, None for the first item or contribution.
        until: The end of the time range, excluded; None for now.
        now: The time now: the end of a range without one.
        tz: The time zone of the days.

    Returns:
        ``size`` (``day``, ``week`` or ``month``), ``labels`` of the bars, and for each bar
        ``opened``, ``closed``, ``contributions`` and ``newcomers``; no labels without data.
    """
    items = Item.objects.filter(repository__in=repositories, kind=kind)
    events = contribution_events(repositories, kind)
    end = until or now
    start = since or min(
        (
            found
            for found in (
                items.aggregate(first=Min("created_at"))["first"],
                events.aggregate(first=Min("at"))["first"],
            )
            if found is not None
        ),
        default=None,
    )
    if start is None or start >= end:
        return {"size": "", "labels": []} | {name: [] for name in SERIES}
    size = size_of(start, end)

    def per_bar(query, field: str) -> list[int]:
        times = in_range(query, field, start, end).values_list(field, flat=True)
        return count_by(times.iterator(), start, end, size, tz)

    return {
        "size": size,
        "labels": [label(day, size) for day in buckets(start, end, size, tz)],
        "opened": per_bar(items, "created_at"),
        "closed": per_bar(items.filter(closed_at__isnull=False), "closed_at"),
        "contributions": per_bar(events, "at"),
        "newcomers": count_by(
            (at for _, at in first_contributions(repositories, kind)), start, end, size, tz
        ),
    }
