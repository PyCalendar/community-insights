"""Pull requests or issues per day, week or month: for the charts of the page Trends."""

from datetime import datetime, tzinfo

from django.db.models import Min

from ..models import Item
from .kind_trend import contribution_events, first_contributions, in_range
from .periods import SIZES, buckets, count_by, exposure, label, people_by, size_of

MOST_CHOSEN = 400  # bars of a length chosen by the reader, at most

# the numbers per bar, by their keys in what kind_series returns
SERIES = ("opened", "closed", "merged", "contributions", "contributors", "newcomers")


def kind_series(
    repositories,
    kind: str,
    since: datetime | None,
    until: datetime | None,
    now: datetime,
    tz: tzinfo,
    size: str = "",
) -> dict:
    """Opened, closed, merged, contributions, contributors, newcomers per bar of a chart.

    For pull requests or for issues, in each day, week, month or year of the time range.

    Args:
        repositories: The repositories.
        kind: ``pr`` or ``issue``.
        since: The start of the time range, None for the first item or contribution.
        until: The end of the time range, excluded; None for now.
        now: The time now: the end of a range without one.
        tz: The time zone of the days.
        size: ``day``, ``week``, ``month`` or ``year``; "" chooses (`periods.size_of`). A
            choice that would make more than ``MOST_CHOSEN`` bars is replaced by one that
            does not.

    Returns:
        ``size`` (``day``, ``week``, ``month`` or ``year``), ``labels`` of the bars, and for
        each bar
        ``opened``, ``closed``, ``merged``, ``contributions``, ``contributors`` (each person
        once per bar) and ``newcomers``, and the ``exposure`` of each bar (the part of it
        inside the time range); ``closed``
        of pull requests are those closed without being merged, ``merged`` is empty for
        issues; no labels without data.
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
        return {"size": "", "labels": [], "exposure": []} | {name: [] for name in SERIES}
    chosen = size if size in SIZES else ""
    if chosen and len(buckets(start, end, chosen, tz)) > MOST_CHOSEN:
        chosen = ""  # days of ten years would be thousands of bars
    size = chosen or size_of(start, end, tz)
    closed = items.filter(closed_at__isnull=False)
    pr = kind == Item.PR

    def per_bar(query, field: str) -> list[int]:
        times = in_range(query, field, start, end).values_list(field, flat=True)
        return count_by(times.iterator(), start, end, size, tz)

    return {
        "size": size,
        "labels": [label(day, size) for day in buckets(start, end, size, tz)],
        "exposure": exposure(start, end, size, tz),
        "opened": per_bar(items, "created_at"),
        "closed": per_bar(closed.filter(merged=False) if pr else closed, "closed_at"),
        "merged": per_bar(closed.filter(merged=True), "closed_at") if pr else [],
        "contributions": per_bar(events, "at"),
        "contributors": people_by(
            in_range(events, "at", start, end).values_list("actor", "at").iterator(),
            start,
            end,
            size,
            tz,
        ),
        "newcomers": count_by(
            (at for _, at in first_contributions(repositories, kind)), start, end, size, tz
        ),
    }
