"""How long pull requests and issues waited for their first response."""

from datetime import datetime, timedelta

import numpy
from django.utils import timezone

from ..models import Event, Item
from .selection import items_in

BUCKETS: list[tuple[str, timedelta]] = [
    ("1h", timedelta(hours=1)),
    ("3h", timedelta(hours=3)),
    ("6h", timedelta(hours=6)),
    ("12h", timedelta(hours=12)),
    ("24h", timedelta(hours=24)),
    ("2d", timedelta(days=2)),
    ("3d", timedelta(days=3)),
    ("5d", timedelta(days=5)),
    ("1w", timedelta(weeks=1)),
    ("2w", timedelta(weeks=2)),
    ("3w", timedelta(weeks=3)),
]
SLOWER = "> 3w"

# The time in seconds until the first response of each class (by name).
Times = dict[str, float]


def response_entries(
    repositories, classifier, since: datetime | None = None, until: datetime | None = None
) -> dict[str, list[Times]]:
    """The time until the first response of each class, per item.

    Per kind, one entry for each item: the seconds until the first response of each class that
    responded. A response is a comment or review by someone other than the author, so a bot that
    answers first does not hide the others. The items are those created in the time range.

    Args:
        repositories: The repositories.
        classifier: Decides the class of each actor.
        since: The start of the time range, None for the beginning.
        until: The end of the time range, excluded; None for now.

    Returns:
        The entries by kind: ``pr`` and ``issue``.
    """
    return response_times(repositories, classifier, since, until)[0]


def response_rows(
    repositories, classifier, since: datetime | None = None, until: datetime | None = None
) -> dict[str, list[tuple[datetime, Times, float]]]:
    """For each item: when it was created, its response times and how long it was observed.

    Args:
        repositories: The repositories.
        classifier: Decides the class of each actor.
        since: The start of the time range, None for the beginning.
        until: The end of the time range, excluded; None for now.

    Returns:
        By kind, for each item the time it was created, the seconds until the first response
        of each class (see ``response_entries``) and the seconds it was observed: until it was
        closed, or until now.
    """
    now = timezone.now()
    items = items_in(repositories, since, until)
    info = {
        pk: (kind, author.lower(), created, closed)
        for pk, kind, author, created, closed in items.values_list(
            "id", "kind", "author", "created_at", "closed_at"
        )
    }
    found: dict[int, Times] = {pk: {} for pk in info}
    events = (
        Event.objects.filter(item__in=info.keys())
        .exclude(kind=Event.OPENED)
        .order_by("at")
        .values_list("item_id", "actor", "association", "is_bot", "at")
    )
    for pk, actor, association, bot, at in events.iterator():
        person_class = classifier(actor, association, bot)
        _, author, created, _ = info[pk]
        if person_class is None or actor.lower() == author:
            continue
        found[pk].setdefault(person_class.name, max((at - created).total_seconds(), 0))
    rows: dict[str, list[tuple[datetime, Times, float]]] = {Item.PR: [], Item.ISSUE: []}
    for pk, (kind, _, created, closed) in info.items():
        rows[kind].append((created, found[pk], max(((closed or now) - created).total_seconds(), 0)))
    return rows


def response_times(
    repositories, classifier, since: datetime | None = None, until: datetime | None = None
) -> tuple[dict[str, list[Times]], dict[str, list[float]]]:
    """The response times and how long each item was observed.

    The entries of response_entries, and per kind for each item the seconds it was observed:
    until it was closed, or until now. An item without a response of a class waited at least
    that long for it (censored data).

    Args:
        repositories: The repositories.
        classifier: Decides the class of each actor.
        since: The start of the time range, None for the beginning.
        until: The end of the time range, excluded; None for now.

    Returns:
        The entries by kind, and the seconds each item was observed by kind.
    """
    rows = response_rows(repositories, classifier, since, until)
    result = {kind: [times for _, times, _ in found] for kind, found in rows.items()}
    observed = {kind: [seconds for _, _, seconds in found] for kind, found in rows.items()}
    return result, observed


def bucket(seconds: float) -> str:
    """The label of the bar of the chart a time falls into.

    Args:
        seconds: The time until the response.

    Returns:
        The label, such as ``3h``.
    """
    return next((label for label, limit in BUCKETS if seconds <= limit.total_seconds()), SLOWER)


def histogram(entries: list[Times], names: list[str]) -> list[tuple[str, dict[str, int]]]:
    """For each bar of the chart, how many first responses of each class fall into it.

    Args:
        entries: The seconds until the first response of each class, one dictionary per item.
        names: The classes to count.

    Returns:
        For each bar, its label and the number of each class.
    """
    labels = [label for label, _ in BUCKETS] + [SLOWER]
    counted = {label: dict.fromkeys(names, 0) for label in labels}
    for entry in entries:
        for name, seconds in entry.items():
            if name in names:
                counted[bucket(seconds)][name] += 1
    return [(label, counted[label]) for label in labels]


def percentile(values: list[float], p: float) -> float | None:
    """The p-th percentile (0-100), as `numpy.percentile` (linear); None without data.

    Args:
        values: The values.
        p: The percentile, 0 to 100.

    Returns:
        The value, or None.
    """
    if not len(values):
        return None
    return float(numpy.percentile(values, p))


def class_percentile(entries: list[Times], name: str | None, p: float) -> tuple[float | None, int]:
    """A percentile of the time until the first response.

    Percentile of the time until the first response of a class, or of the first response of any
    class if name is None; and the number of responses.

    Args:
        entries: The seconds until the first response of each class, one dictionary per item.
        name: The class, None for the first response of anybody.
        p: The percentile, 0 to 100.

    Returns:
        The seconds, None without responses, and how many responses there are.
    """
    if name is None:
        seconds = [min(e.values()) for e in entries if e]
    else:
        seconds = [e[name] for e in entries if name in e]
    return percentile(seconds, p), len(seconds)
