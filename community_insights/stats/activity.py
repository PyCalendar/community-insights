"""When one person was active."""

from collections import defaultdict
from datetime import datetime

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


def by_hour_and_weekday(times: list[datetime], tz) -> list[list[int]]:
    """A 7 x 24 grid (Monday first) of the number of times in the timezone.

    Args:
        times: The times.
        tz: The time zone.

    Returns:
        The grid.
    """
    grid = [[0] * 24 for _ in range(7)]
    for time in times:
        local = time.astimezone(tz)
        grid[local.weekday()][local.hour] += 1
    return grid


def by_month_and_kind(
    activity: list[tuple[datetime, str]], tz
) -> dict[tuple[int, int], dict[str, int]]:
    """How many activities of each kind each month had, in the time zone.

    Args:
        activity: Pairs of a time and a kind.
        tz: The time zone.

    Returns:
        The number of each kind by (year, month).
    """
    months: dict[tuple[int, int], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for time, kind in activity:
        local = time.astimezone(tz)
        months[(local.year, local.month)][kind] += 1
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
    months: dict[tuple[int, int], list[float]] = defaultdict(list)
    for event in first.values():
        local = event.at.astimezone(tz)
        months[(local.year, local.month)].append(
            max((event.at - event.item.created_at).total_seconds(), 0)
        )
    return months
