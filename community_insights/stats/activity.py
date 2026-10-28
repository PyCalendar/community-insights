"""When one person was active, grouped by month, weekday and hour with pandas."""

from datetime import datetime
from typing import cast

import pandas as pd

from ..models import Commit, Event, Item
from .selection import events_in


def activity_of(
    repositories, login: str, since: datetime | None = None, until: datetime | None = None
) -> list[tuple[datetime, str]]:
    """Time and kind of everything one person did in the repositories.

    Args:
        repositories: The repositories.
        login: The handle, in any case.
        since: The start of the time range, None for the beginning.
        until: The end of the time range, excluded; None for now.

    Returns:
        Pairs of a time and a kind, such as ``comment``.
    """
    events = events_in(
        Event.objects.filter(item__repository__in=repositories, actor__iexact=login),
        since,
        until,
    ).select_related("item")
    result = []
    for event in events:
        if event.kind == Event.OPENED:
            kind = "pull request" if event.item.kind == Item.PR else "issue"
        else:
            kind = event.kind
        result.append((event.at, kind))
    commits = Commit.objects.filter(repository__in=repositories, author__iexact=login)
    if since:
        commits = commits.filter(at__gte=since)
    if until:
        commits = commits.filter(at__lt=until)
    result += [(at, "commit") for at in commits.values_list("at", flat=True)]
    return result


def local_times(times, tz) -> pd.Series:
    """Times as a pandas series in the time zone.

    Args:
        times: Aware times.
        tz: The time zone.

    Returns:
        The times, converted.
    """
    return pd.Series(
        pd.to_datetime(list(times), utc=True), dtype="datetime64[ns, UTC]"
    ).dt.tz_convert(tz)


def by_hour_and_weekday(times: list[datetime], tz) -> list[list[int]]:
    """A 7 x 24 grid (Monday first) of the number of times in the timezone.

    Args:
        times: The times.
        tz: The time zone.

    Returns:
        The grid.

    Examples:
        >>> from datetime import UTC
        >>> grid = by_hour_and_weekday([datetime(2026, 1, 5, 23, tzinfo=UTC)], UTC)
        >>> grid[0][23], sum(map(sum, grid))
        (1, 1)
    """
    local = local_times(times, tz)
    grid = pd.crosstab(local.dt.weekday, local.dt.hour)
    return grid.reindex(index=range(7), columns=range(24), fill_value=0).astype(int).values.tolist()


def by_month_and_kind(
    activity: list[tuple[datetime, str]], tz
) -> dict[tuple[int, int], dict[str, int]]:
    """How many activities of each kind each month had, in the time zone.

    Args:
        activity: Pairs of a time and a kind.
        tz: The time zone.

    Returns:
        The number of each kind by (year, month).

    Examples:
        >>> from datetime import UTC
        >>> by_month_and_kind([(datetime(2026, 1, 31, 23, tzinfo=UTC), "commit")], UTC)
        {(2026, 1): {'commit': 1}}
    """
    if not activity:
        return {}
    local = local_times([time for time, _ in activity], tz)
    frame = pd.DataFrame(
        {"year": local.dt.year, "month": local.dt.month, "kind": [kind for _, kind in activity]}
    )
    months: dict[tuple[int, int], dict[str, int]] = {}
    for key, count in frame.groupby(["year", "month", "kind"]).size().items():
        year, month, kind = cast(tuple, key)  # grouped by three columns
        months.setdefault((int(year), int(month)), {})[str(kind)] = int(count)
    return months


def responses_by_month(
    repositories, login: str, tz, since: datetime | None = None, until: datetime | None = None
) -> dict[tuple[int, int], list[float]]:
    """The time until a person's first responses, by month.

    The seconds until the first response of a person on each item of others, by the month (in
    the time zone) of the response.

    Args:
        repositories: The repositories.
        login: The handle of the person.
        tz: The time zone of the months.
        since: The start of the time range, None for the beginning.
        until: The end of the time range, excluded; None for now.

    Returns:
        The seconds by (year, month).
    """
    events = events_in(
        Event.objects.filter(item__repository__in=repositories, actor__iexact=login).exclude(
            kind=Event.OPENED
        ),
        since,
        until,
    ).select_related("item")
    first: dict[int, Event] = {}
    for event in events.order_by("at"):
        if event.item.author.lower() != login.lower():
            first.setdefault(event.item_id, event)
    if not first:
        return {}
    responses = list(first.values())
    local = local_times([event.at for event in responses], tz)
    frame = pd.DataFrame(
        {
            "year": local.dt.year,
            "month": local.dt.month,
            "seconds": [max((e.at - e.item.created_at).total_seconds(), 0) for e in responses],
        }
    )
    months: dict[tuple[int, int], list[float]] = {}
    for key, group in frame.groupby(["year", "month"]):
        year, month = cast(tuple, key)  # grouped by two columns
        months[(int(year), int(month))] = group["seconds"].tolist()
    return months
