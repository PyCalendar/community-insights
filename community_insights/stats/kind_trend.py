"""How pull requests or issues changed in a time range, next to the period before it."""

from dataclasses import dataclass
from datetime import datetime

from django.db.models.functions import Lower

from ..models import Event, Item
from .change import Change
from .periods import previous


@dataclass(frozen=True)
class KindTrend:
    """The numbers of pull requests or of issues in a time range and in the period before.

    Attributes:
        kind: ``pr`` or ``issue``.
        opened: How many were opened.
        closed: How many were closed, merged pull requests included.
        merged: How many pull requests were merged, a part of ``closed``; None for issues.
        contributions: Openings, comments and reviews by people, not bots.
        contributors: How many people, not bots, made the contributions.
        newcomers: How many people made their first contribution to this kind in the
            repositories: the first that the site has read.
        newcomer_logins: The handles of the new contributors of the time range, the first
            one first.
    """

    kind: str
    opened: Change
    closed: Change
    merged: Change | None
    contributions: Change
    contributors: Change
    newcomers: Change
    newcomer_logins: tuple[str, ...]


def within(at: datetime, start: datetime | None, end: datetime | None) -> bool:
    """Whether a time is in a time range.

    Args:
        at: The time.
        start: The start, None for the beginning.
        end: The end, excluded; None for now.

    Returns:
        Whether it is in the range.

    Examples:
        >>> from datetime import UTC
        >>> day = datetime(2026, 1, 2, tzinfo=UTC)
        >>> within(day, None, None), within(day, day, None), within(day, None, day)
        (True, True, False)
    """
    return (start is None or at >= start) and (end is None or at < end)


def contribution_events(repositories, kind: str):
    """The openings, comments and reviews of people, not bots, on pull requests or issues.

    Args:
        repositories: The repositories.
        kind: ``pr`` or ``issue``.

    Returns:
        The events, as a query without an order.
    """
    return Event.objects.filter(
        item__repository__in=repositories, item__kind=kind, is_bot=False
    ).order_by()


def first_contributions(repositories, kind: str) -> list[tuple[str, datetime]]:
    """When each person, not a bot, contributed to pull requests or issues for the first time.

    The handles are compared in any case, as GitHub does; each is written as in its first
    contribution.

    Args:
        repositories: The repositories.
        kind: ``pr`` or ``issue``.

    Returns:
        The handle and the time of the first contribution of each person, the first one first.
    """
    first: dict[str, tuple[str, datetime]] = {}
    events = contribution_events(repositories, kind).order_by("at", "pk")
    for actor, at in events.values_list("actor", "at").iterator():
        first.setdefault(actor.lower(), (actor, at))
    return list(first.values())


def in_range(query, field: str, start: datetime | None, end: datetime | None):
    """The rows of a query with a time in a time range.

    Args:
        query: The rows.
        field: The field of the time, such as ``created_at``.
        start: The start, None for the beginning.
        end: The end, excluded; None for now.

    Returns:
        The rows in the range, as a query.
    """
    if start is not None:
        query = query.filter(**{f"{field}__gte": start})
    if end is not None:
        query = query.filter(**{f"{field}__lt": end})
    return query


def kind_trend(
    repositories, kind: str, since: datetime | None, until: datetime | None, now: datetime
) -> KindTrend:
    """The numbers of pull requests or issues in a time range, next to the period before it.

    Args:
        repositories: The repositories.
        kind: ``pr`` or ``issue``.
        since: The start of the time range, None for the beginning.
        until: The end of the time range, excluded; None for now.
        now: The time now: the end of a range without one.

    Returns:
        The numbers; without a start, nothing is compared (``Change.before`` is None).
    """
    before = previous(since, until, now)
    items = Item.objects.filter(repository__in=repositories, kind=kind)
    closed = items.filter(closed_at__isnull=False)
    events = contribution_events(repositories, kind)

    def change(query, field: str) -> Change:
        return Change(
            in_range(query, field, since, until).count(),
            in_range(query, field, *before).count() if before else None,
        )

    def people(start: datetime | None, end: datetime | None) -> int:
        found = in_range(events, "at", start, end).annotate(person=Lower("actor"))
        return found.values("person").distinct().count()

    firsts = first_contributions(repositories, kind)
    newcomers = tuple(login for login, at in firsts if within(at, since, until))
    return KindTrend(
        kind=kind,
        opened=change(items, "created_at"),
        closed=change(closed, "closed_at"),
        merged=change(closed.filter(merged=True), "closed_at") if kind == Item.PR else None,
        contributions=change(events, "at"),
        contributors=Change(people(since, until), people(*before) if before else None),
        newcomers=Change(
            len(newcomers),
            sum(within(at, *before) for _, at in firsts) if before else None,
        ),
        newcomer_logins=newcomers,
    )
