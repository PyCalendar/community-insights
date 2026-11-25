"""The suggestions of pull requests, grouped by pull request, for the pages of suggestions."""

from dataclasses import dataclass, field
from datetime import datetime

from ..models import Item, Suggestion
from ..sync.suggestions import STATUSES
from .suggestion_summary import SuggestionSummary


@dataclass
class PullSuggestions:
    """A pull request with its suggestions.

    Attributes:
        item: The pull request.
        suggestions: Its suggestions, unknown first, then open, then applied, then by time.
        summary: How many are applied, open and unknown: of all of its suggestions, also
            those the filter leaves out.
    """

    item: Item
    suggestions: list[Suggestion] = field(default_factory=list)
    summary: SuggestionSummary = field(default_factory=SuggestionSummary)

    @property
    def rank(self) -> int:
        """The place of its most urgent suggestion: 0 unknown, 1 open, 2 applied."""
        return min((STATUSES.index(s.status) for s in self.suggestions), default=len(STATUSES))


def rank_of(suggestion: Suggestion) -> tuple:
    """The order of suggestions: unknown, open, applied; then by time.

    Args:
        suggestion: A suggestion.

    Returns:
        The key to sort by.
    """
    return (STATUSES.index(suggestion.status), suggestion.created_at)


def pull_suggestions(
    repositories,
    since: datetime | None = None,
    until: datetime | None = None,
    author: str | None = None,
    statuses=STATUSES,
    pull: tuple[str, int] | None = None,
) -> list[PullSuggestions]:
    """The pull requests with suggestions, unknown ones first, then open, then applied.

    Args:
        repositories: The repositories.
        since: The start of the time range of the suggestions, None for the beginning.
        until: Its end, excluded; None for now.
        author: Only the pull requests of this author, in any case; None for everybody.
        statuses: The statuses to show; the summaries count all.
        pull: Only this pull request: the full name of the repository and the number.

    Returns:
        The pull requests with a shown suggestion, by their most urgent suggestion and then
        by repository and number.
    """
    found = Suggestion.objects.filter(item__repository__in=repositories).select_related(
        "item", "item__repository"
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
        group.suggestions.sort(key=rank_of)
        if group.suggestions:
            shown.append(group)
    return sorted(shown, key=lambda g: (g.rank, g.item.repository.full_name.lower(), g.item.number))


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
