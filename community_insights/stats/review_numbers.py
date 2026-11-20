"""The reviews of pull requests: how many, by whom, of which kind, and until a merge."""

import statistics
from dataclasses import dataclass, field
from datetime import datetime

from ..classify import MEMBERS
from ..models import Event, Item
from .change import Change
from .kind_trend import in_range
from .periods import previous

# the kinds of review that GitHub knows, and the rest (dismissed, or read before the kinds)
KINDS = ("approved", "changes_requested", "commented", "other")
# the bars of the reviews until a merge: 0 to 4, and 5 or more
MOST_BARS = 5


def kind_of(state: str) -> str:
    """The kind of a review for the page: one of ``KINDS``.

    Args:
        state: The state stored with the review, such as ``approved``; "" if unknown.

    Returns:
        The kind.

    Examples:
        >>> kind_of("approved"), kind_of("dismissed"), kind_of("")
        ('approved', 'other', 'other')
    """
    return state if state in KINDS else "other"


def by_collaborator(association: str) -> bool:
    """Whether a review is by a collaborator: an owner, a member or a collaborator.

    Args:
        association: The status of the reviewer in the repository, as GitHub names it.

    Returns:
        True for collaborators, False for people from outside.

    Examples:
        >>> by_collaborator("MEMBER"), by_collaborator("contributor"), by_collaborator("")
        (True, False, False)
    """
    return association.lower() in MEMBERS


def review_events(repositories):
    """The reviews of pull requests by people, not bots, and not by the author.

    Args:
        repositories: The repositories.

    Returns:
        The query of the reviews, with the author of their pull request.
    """
    return (
        Event.objects.filter(
            item__repository__in=repositories, item__kind=Item.PR, kind=Event.REVIEW, is_bot=False
        )
        .order_by()
        .values_list("actor", "item__author", "association", "state", "at", "item_id")
    )


def of_others(rows) -> list[tuple]:
    """The reviews that are not by the author of the pull request, in any case.

    Args:
        rows: The rows of ``review_events``.

    Returns:
        The rows.
    """
    return [row for row in rows if row[0].lower() != (row[1] or "").lower()]


@dataclass
class ReviewNumbers:
    """The reviews of a time range, next to the time before it, and the reviews until merged.

    Attributes:
        total: How many reviews were given.
        collaborators: Of those, by owners, members and collaborators of the repository.
        others: Of those, by people from outside: contributors, first-time contributors and
            people without a status.
        reviewers: How many people gave them.
        kinds: For each of ``KINDS``: the reviews by collaborators and by others.
        merged: For each pull request merged in the time range: its reviews before the merge.
    """

    total: Change
    collaborators: Change
    others: Change
    reviewers: int = 0
    kinds: dict[str, list[int]] = field(default_factory=dict)
    merged: list[int] = field(default_factory=list)

    @property
    def histogram(self) -> list[int]:
        """How many merged pull requests had 0, 1, 2, 3, 4, and 5 or more reviews.

        Examples:
            >>> numbers = ReviewNumbers(Change(0), Change(0), Change(0), merged=[0, 2, 2, 7])
            >>> numbers.histogram
            [1, 0, 2, 0, 0, 1]
        """
        found = [0] * (MOST_BARS + 1)
        for count in self.merged:
            found[min(count, MOST_BARS)] += 1
        return found

    @property
    def median(self) -> float | None:
        """The median of the reviews until merged; None without merged pull requests."""
        return statistics.median(self.merged) if self.merged else None

    @property
    def mean(self) -> float | None:
        """The mean of the reviews until merged; None without merged pull requests."""
        return statistics.fmean(self.merged) if self.merged else None

    @property
    def without(self) -> int:
        """How many pull requests were merged without a review."""
        return sum(count == 0 for count in self.merged)


def review_numbers(
    repositories, since: datetime | None, until: datetime | None, now: datetime
) -> ReviewNumbers:
    """The reviews of a time range by collaborators and others, of each kind, until merged.

    A review counts when a person, not a bot and not the author of the pull request, gave
    it: an approval, a request for changes or a comment as a review.

    Args:
        repositories: The repositories.
        since: The start of the time range, None for the beginning.
        until: The end of the time range, excluded; None for now.
        now: The time now: the end of a range without one.

    Returns:
        The numbers; without a start, nothing is compared (``Change.before`` is None).
    """
    rows = of_others(review_events(repositories))
    before = previous(since, until, now)

    def within(at: datetime, start, end) -> bool:
        return (start is None or at >= start) and (end is None or at < end)

    def count(start, end, collaborators: bool | None = None) -> int:
        return sum(
            within(at, start, end)
            and (collaborators is None or by_collaborator(association) == collaborators)
            for _, _, association, _, at, _ in rows
        )

    def change(collaborators: bool | None = None) -> Change:
        return Change(
            count(since, until, collaborators),
            count(*before, collaborators) if before else None,
        )

    kinds = {kind: [0, 0] for kind in KINDS}
    reviewers = set()
    for actor, _, association, state, at, _ in rows:
        if within(at, since, until):
            kinds[kind_of(state)][0 if by_collaborator(association) else 1] += 1
            reviewers.add(actor.lower())
    merges = in_range(
        # GitHub knows when each was merged; one without the time cannot be placed
        Item.objects.filter(
            repository__in=repositories, kind=Item.PR, merged=True, closed_at__isnull=False
        ),
        "closed_at",
        since,
        until,
    ).values_list("pk", "closed_at")
    merged_at = dict(merges)
    reviews: dict[int, int] = dict.fromkeys(merged_at, 0)
    for _, _, _, _, at, item in rows:
        if item in merged_at and at <= merged_at[item]:
            reviews[item] += 1
    return ReviewNumbers(
        total=change(),
        collaborators=change(True),
        others=change(False),
        reviewers=len(reviewers),
        kinds=kinds,
        merged=list(reviews.values()),
    )
