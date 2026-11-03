"""Fetch what changed before a page or a badge is shown, waiting a few seconds at most.

The page of replies and its badges queue a fetch of the repositories that were not fetched
for a while (``AUTO_FETCH_AFTER_MINUTES``) and wait until it is done, at most
``AUTO_FETCH_TIMEOUT`` seconds; then they show what is in the database. The worker reads
GitHub, as for every fetch; the page only waits. Without points left in the tokens they may
use, they do not fetch and do not wait.
"""

import time
from collections.abc import Callable
from datetime import datetime, timedelta
from types import SimpleNamespace

from django.conf import settings
from django.utils import timezone

from ..models import FetchJob
from .estimate import Estimate
from .jobs import enqueue


def unasked(token: str) -> SimpleNamespace:
    """A client that is never asked: the points left come from what this site counted.

    Each token gets its own, as a token entry writes its limits into its client.

    Args:
        token: The token, not used.

    Returns:
        The client, with an unknown rate.
    """
    return SimpleNamespace(rate=SimpleNamespace(remaining=None, reset_at=None))


POLL = 0.25  # seconds between looking at the jobs


def outdated(repositories, now: datetime) -> list:
    """The repositories to fetch again: read before, but not for a while.

    A repository that was never read needs the page Fetch, with its estimate; one with a
    job of the last minutes (also a failed one) is not queued again.

    Args:
        repositories: The repositories.
        now: The time now.

    Returns:
        The repositories.
    """
    after = now - timedelta(minutes=settings.AUTO_FETCH_AFTER_MINUTES)
    recent = set(
        FetchJob.objects.filter(repository__in=repositories, created__gte=after).values_list(
            "repository", flat=True
        )
    )
    return [
        r
        for r in repositories
        if r.fetched_at is not None and r.fetched_at < after and r.pk not in recent
    ]


def has_points(user, now: datetime, use=None) -> bool:
    """Whether the tokens a fetch of the user would use have points left in this hour.

    Args:
        user: Whose tokens; None for the tokens shared on this site.
        now: The time now.
        use: The public use of the fetch (``tokens.Use``), whose grants count too.

    Returns:
        True if a token has points left or no limit.
    """
    from ..tokens.access import entries_for, points_left

    entries = entries_for(user, make_client=unasked, use=use)
    if not entries:
        return False
    left = points_left(entries, now)
    return left["unlimited"] or left["total"] > 0


def refresh(
    repositories,
    user,
    reason: str,
    reason_url: str = "",
    timeout: float | None = None,
    use=None,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> bool:
    """Fetch the repositories that may have changed, and wait for it.

    Args:
        repositories: The repositories of the page.
        user: Whose tokens read: the person who shares the page; None for the shared ones.
        reason: Why, shown on the page Downloads.
        reason_url: The page that asked.
        timeout: The most seconds to wait; None for ``AUTO_FETCH_TIMEOUT``, 0 to never fetch.
        use: The public use (``tokens.Use``): the grants of tokens for it may read too.
        sleep: Waits so many seconds; tests give one that waits not.
        clock: Seconds that count up; tests give their own.

    Returns:
        True if a fetch ran and finished in time, False if none was needed or possible, or
        it did not finish in time; then it continues and the page shows what is there.
    """
    seconds: float = settings.AUTO_FETCH_TIMEOUT if timeout is None else timeout
    if seconds <= 0:
        return False
    now = timezone.now()
    found = outdated(list(repositories), now)
    if not found or not has_points(user, now, use):
        return False
    jobs = enqueue(
        user,
        [Estimate(repository=r, prs=None, issues=None, cached=0, points=1) for r in found],
        reason=reason,
        reason_url=reason_url,
        use=use,
    )
    if not jobs:
        return False
    end = clock() + seconds
    ids = [job.pk for job in jobs]
    while FetchJob.objects.filter(pk__in=ids, status__in=FetchJob.ACTIVE).exists():
        if clock() >= end:
            return False
        sleep(POLL)
    return True
