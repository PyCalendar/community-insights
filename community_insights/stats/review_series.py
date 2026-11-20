"""Reviews per day, week, month or year, by collaborators and by others: the page Reviews."""

from datetime import datetime, tzinfo

from .periods import SIZES, buckets, count_by, exposure, label, size_of
from .review_numbers import by_collaborator, of_others, review_events

MOST_CHOSEN = 400  # bars of a length chosen by the reader, at most


def review_series(
    repositories,
    since: datetime | None,
    until: datetime | None,
    now: datetime,
    tz: tzinfo,
    size: str = "",
) -> dict:
    """The reviews by collaborators and by others in each bar of the time range.

    Args:
        repositories: The repositories.
        since: The start of the time range, None for the first review.
        until: The end of the time range, excluded; None for now.
        now: The time now: the end of a range without one.
        tz: The time zone of the days.
        size: ``day``, ``week``, ``month`` or ``year``; "" chooses (`periods.size_of`).

    Returns:
        ``size``, ``labels``, ``exposure`` and, per bar, ``total``, ``collaborators`` and
        ``others``; no labels without reviews.
    """
    rows = of_others(review_events(repositories))
    end = until or now
    start = since or min((at for *_, at, _ in rows), default=None)
    empty = {
        "size": "",
        "labels": [],
        "exposure": [],
        "total": [],
        "collaborators": [],
        "others": [],
    }
    if start is None or start >= end:
        return empty
    chosen = size if size in SIZES else ""
    if chosen and len(buckets(start, end, chosen, tz)) > MOST_CHOSEN:
        chosen = ""
    size = chosen or size_of(start, end, tz)

    def per_bar(collaborators: bool | None) -> list[int]:
        times = (
            at
            for _, _, association, _, at, _ in rows
            if collaborators is None or by_collaborator(association) == collaborators
        )
        return count_by(times, start, end, size, tz)

    return {
        "size": size,
        "labels": [label(day, size) for day in buckets(start, end, size, tz)],
        "exposure": exposure(start, end, size, tz),
        "total": per_bar(None),
        "collaborators": per_bar(True),
        "others": per_bar(False),
    }
