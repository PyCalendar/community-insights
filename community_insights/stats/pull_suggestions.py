"""The suggestions of pull requests, grouped by pull request, for the pages of suggestions."""

from dataclasses import dataclass, field
from datetime import datetime

from django.db.models import Q

from ..models import Item, Suggestion
from ..sync.suggestions import STATUSES
from .suggestion_summary import SuggestionSummary

OPEN, CLOSED, MERGED = "open", "closed", "merged"
PULL_STATES = (OPEN, CLOSED, MERGED)  # of the pull requests: closed is closed without merge
SHOWN_STATES = (OPEN,)  # the pages show the suggestions of open pull requests first


def states_query(states) -> Q:
    """The pull requests in some states.

    Args:
        states: ``open``, ``closed`` (without merge) and ``merged``.

    Returns:
        The condition of the suggestions; one that matches nothing without states.

    Examples:
        >>> states_query(["open"])
        <Q: (AND: ('item__state', 'open'))>
    """
    query = Q(pk__in=[])
    if OPEN in states:
        query = Q(item__state="open")
    if CLOSED in states:
        query |= Q(item__state="closed", item__merged=False)
    if MERGED in states:
        query |= Q(item__state="closed", item__merged=True)
    return query


@dataclass
class PullSuggestions:
    """A pull request with its suggestions.

    Attributes:
        item: The pull request.
        suggestions: Its suggestions, newest first.
        summary: How many are applied, open and unknown: of all of its suggestions, also
            those the filter leaves out.
    """

    item: Item
    suggestions: list[Suggestion] = field(default_factory=list)
    summary: SuggestionSummary = field(default_factory=SuggestionSummary)

    @property
    def latest(self) -> datetime | None:
        """The time of its newest suggestion shown."""
        return max((s.created_at for s in self.suggestions if s.created_at), default=None)


def newest_first(suggestion: Suggestion) -> tuple:
    """The order of suggestions: the newest first; then by their id.

    Args:
        suggestion: A suggestion.

    Returns:
        The key to sort by, descending.
    """
    return (suggestion.created_at.timestamp() if suggestion.created_at else 0, suggestion.pk)


def pull_suggestions(
    repositories,
    since: datetime | None = None,
    until: datetime | None = None,
    author: str | None = None,
    statuses=STATUSES,
    pull: tuple[str, int] | None = None,
    states=PULL_STATES,
) -> list[PullSuggestions]:
    """The pull requests with suggestions, the one with the newest suggestion first.

    Args:
        repositories: The repositories.
        since: The start of the time range of the suggestions, None for the beginning.
        until: Its end, excluded; None for now.
        author: Only the pull requests of this author, in any case; None for everybody.
        statuses: The statuses to show; the summaries count all.
        pull: Only this pull request: the full name of the repository and the number.
        states: The states of the pull requests to show (``PULL_STATES``).

    Returns:
        The pull requests with a shown suggestion, by their newest shown suggestion, newest
        first; then by repository and number.
    """
    found = (
        Suggestion.objects.filter(item__repository__in=repositories)
        .filter(states_query(states))
        .select_related("item", "item__repository")
    )
    if since:
        found = found.filter(created_at__gte=since)
    if until:
        found = found.filter(created_at__lt=until)
    if author:
        found = found.filter(item__author__iexact=author)
    if pull:
        found = found.filter(item__repository__full_name=pull[0], item__number=pull[1])
    groups: dict[int, PullSuggestions] = {}
    everything: dict[int, list[str]] = {}
    for suggestion in found:
        everything.setdefault(suggestion.item_id, []).append(suggestion.status)
        group = groups.setdefault(suggestion.item_id, PullSuggestions(suggestion.item))
        if suggestion.status in statuses:
            group.suggestions.append(suggestion)
    shown = []
    for pk, group in groups.items():
        group.summary = SuggestionSummary.of(everything[pk])
        group.suggestions.sort(key=newest_first, reverse=True)
        if group.suggestions:
            shown.append(group)
    shown.sort(key=lambda g: (g.item.repository.full_name.lower(), g.item.number))
    return sorted(shown, key=lambda g: g.latest.timestamp() if g.latest else 0, reverse=True)


def summarize_suggestions(
    repositories,
    author: str | None = None,
    pull: tuple[str, int] | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> SuggestionSummary:
    """The summary of the suggestions on the pull requests of an author, or of one.

    Args:
        repositories: The repositories.
        author: The author of the pull requests, in any case; None for everybody.
        pull: One pull request: the full name of the repository and the number.
        since: The start of the time range of the suggestions, None for the beginning.
        until: Its end, excluded; None for now.

    Returns:
        How many are applied, open and unknown.
    """
    found = Suggestion.objects.filter(item__repository__in=repositories)
    if since:
        found = found.filter(created_at__gte=since)
    if until:
        found = found.filter(created_at__lt=until)
    if author:
        found = found.filter(item__author__iexact=author)
    if pull:
        found = found.filter(item__repository__full_name=pull[0], item__number=pull[1])
    return SuggestionSummary.of(found.values_list("status", flat=True))
