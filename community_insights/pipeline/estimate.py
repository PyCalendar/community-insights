"""How many API points and how much time reading repositories takes."""

import math
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from datetime import timedelta

from asgiref.sync import sync_to_async
from django.db.models import Count, Q
from django.utils import timezone

from ..models import FetchJob, Item, Repository
from ..sync import PAGE, PEOPLE_BATCH

ASK_ABOVE = 5000  # points: one hour of one token
SECONDS_PER_POINT = 2.0  # until measured


@dataclass
class Estimate:
    """What reading a repository costs: its items on GitHub, those read, and the points.

    Attributes:
        repository: The repository.
        prs: Its pull requests on GitHub, None if not known.
        issues: Its issues on GitHub, None if not known.
        cached: The pull requests and issues read already.
        points: The API points reading it needs, or the requests without a token.
    """

    repository: Repository
    prs: int | None  # on GitHub
    issues: int | None
    cached: int
    points: int

    @property
    def items(self) -> int:
        """Pull requests and issues on GitHub."""
        return (self.prs or 0) + (self.issues or 0)

    @property
    def missing(self) -> int:
        """Items on GitHub that are not read yet."""
        return max(0, self.items - self.cached)


def anonymous_points(repository: Repository, prs: int, issues: int) -> int:
    """Requests to read a repository without a token.

    Requests without a token: pages of 100 items, issue comments and review comments, assumed
    one or two of them per item.

    Args:
        repository: The repository.
        prs: Its pull requests on GitHub.
        issues: Its issues on GitHub.

    Returns:
        The requests.
    """
    items = prs + issues
    return 3 + math.ceil(items / 100) + math.ceil(items * 2 / 100)


def points_for(repository: Repository, prs: int, issues: int, cached: int) -> int:
    """API points to read a repository.

    API points to read a repository: a page per 50 items, some more for items with many
    comments, and the people in batches. Read before: the changes.

    Args:
        repository: The repository.
        prs: Its pull requests on GitHub.
        issues: Its issues on GitHub.
        cached: The pull requests and issues read already.

    Returns:
        The points.
    """
    commits = math.ceil((repository.commits_total or 0) / 100) + 1  # a page per 100 commits
    if repository.prs_synced_until is None and repository.issues_synced_until is None:
        pages = math.ceil(prs / PAGE) + math.ceil(issues / PAGE) or 2
        follow = math.ceil((prs + issues) / 20)  # items with more than a page of comments
        people = math.ceil(min(prs + issues, 3000) * 0.4 / PEOPLE_BATCH)
        return pages + follow + people + commits
    missing = max(0, prs + issues - cached)
    return 2 + math.ceil(missing / PAGE) + 1


def cached_counts(repositories) -> dict[int, dict[str, int]]:
    """The pull requests and issues read of each repository, by its id.

    Args:
        repositories: The repositories.

    Returns:
        The numbers of pull requests and issues read, by the id of each repository.
    """
    rows = (
        Item.objects.filter(repository__in=repositories)
        .values("repository")
        .annotate(
            prs=Count("id", filter=Q(kind=Item.PR)),
            issues=Count("id", filter=Q(kind=Item.ISSUE)),
        )
    )
    return {row["repository"]: {"prs": row["prs"], "issues": row["issues"]} for row in rows}


TOTALS_KEPT = timedelta(minutes=10)  # totals are not asked again for so long


def known_totals(repositories, now) -> dict[str, tuple[int, int]]:
    """The totals asked recently: they are not asked again.

    Args:
        repositories: The repositories.
        now: The time now.

    Returns:
        The pull requests and issues by the name of each repository.
    """
    return {
        r.full_name: (r.prs_total, r.issues_total)
        for r in repositories
        if r.totals_checked_at
        and now - r.totals_checked_at < TOTALS_KEPT
        and r.prs_total is not None
        and r.issues_total is not None
    }


async def estimate(repositories, client, anonymous: bool = False) -> list[Estimate]:
    """Ask GitHub how many items there are.

    Ask GitHub how many items there are (one point per 50 repositories), unless it was asked in
    the last minutes.

    Args:
        repositories: The repositories.
        client: The tokens or the client without a token.
        anonymous: True when the client has no token: its requests are counted instead.

    Returns:
        The estimate of each repository.
    """
    repositories = await sync_to_async(list)(repositories)
    totals = known_totals(repositories, timezone.now())
    unknown = [r.full_name for r in repositories if r.full_name not in totals]
    if unknown:
        totals |= await client.totals(unknown)
    return await sync_to_async(estimates_of)(repositories, totals, set(unknown), anonymous)


def estimates_of(
    repositories, totals: dict, asked: AbstractSet[str] = frozenset(), anonymous: bool = False
) -> list[Estimate]:
    """The estimates for the totals; those just asked are remembered.

    Args:
        repositories: The repositories.
        totals: The pull requests and issues of each repository on GitHub, by its name.
        asked: The names whose totals were just asked: they are stored.
        anonymous: True to count the requests without a token instead of points.

    Returns:
        The estimate of each repository.
    """
    cached = cached_counts(repositories)
    result = []
    for repository in repositories:
        found = totals.get(repository.full_name)
        counts = cached.get(repository.pk, {"prs": 0, "issues": 0})
        have = counts["prs"] + counts["issues"]
        prs = issues = None
        points = 0
        if found:
            prs, issues = found
            if repository.full_name in asked:
                repository.prs_total, repository.issues_total = prs, issues
                repository.totals_checked_at = timezone.now()
                repository.save(update_fields=["prs_total", "issues_total", "totals_checked_at"])
            if anonymous:
                points = anonymous_points(repository, prs, issues)
            else:
                points = points_for(repository, prs, issues, have)
        result.append(Estimate(repository, prs, issues, have, points))
    return result


def seconds_per_point() -> float:
    """Measured from the last finished jobs.

    Returns:
        The seconds one API point takes; ``SECONDS_PER_POINT`` until enough was measured.
    """
    jobs = FetchJob.objects.filter(
        status=FetchJob.DONE, points_used__gt=0, started__isnull=False, finished__isnull=False
    ).order_by("-finished")[:50]
    points = sum(j.points_used for j in jobs)
    seconds = sum(
        (j.finished - j.started).total_seconds() for j in jobs if j.finished and j.started
    )
    return seconds / points if points >= 20 else SECONDS_PER_POINT
