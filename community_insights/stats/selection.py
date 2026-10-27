"""The data in a time range."""

from datetime import datetime

from ..models import Item


def items_in(repositories, since: datetime | None = None, until: datetime | None = None):
    """The pull requests and issues created in the time range (both optional).

    Args:
        repositories: The repositories.
        since: The start of the time range, None for the beginning.
        until: The end of the time range, excluded; None for now.

    Returns:
        The items, as a query.
    """
    items = Item.objects.filter(repository__in=repositories)
    if since:
        items = items.filter(created_at__gte=since)
    if until:
        items = items.filter(created_at__lt=until)
    return items


def events_in(events, since: datetime | None = None, until: datetime | None = None):
    """The events in the time range (both optional).

    Args:
        events: The events, as a query.
        since: The start of the time range, None for the beginning.
        until: The end of the time range, excluded; None for now.

    Returns:
        The events in it.
    """
    if since:
        events = events.filter(at__gte=since)
    if until:
        events = events.filter(at__lt=until)
    return events
