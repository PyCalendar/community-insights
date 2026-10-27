"""The pipeline: get data from GitHub, then run the statistics on it.

The pipeline: (1) get data from GitHub with queued fetch jobs, (2) run the statistics on the data
present. This package estimates the cost of a fetch, queues and runs the jobs and tells how complete
the data is.
"""

from asgiref.sync import async_to_sync

from .completeness import ITEMS_PER_SECOND, Source, completeness, seconds_left, sources
from .estimate import ASK_ABOVE, Estimate, cached_counts, estimate, points_for, seconds_per_point
from .jobs import cancel, claim_next, enqueue, finish, requeue_stale
from .runner import JobRunner
from .worker import run, start_worker, work, work_async


def estimate_for(user, repositories) -> tuple[list[Estimate], list, int]:
    """Estimate with the tokens of a user, from synchronous code.

    Estimate with the tokens of a user, from synchronous code: the estimates, the tokens in
    their order and the points the estimate cost.
    """
    from asgiref.sync import sync_to_async

    from ..github.anonymous import AnonymousClient
    from ..tokens import TokenPool, entries_for

    async def estimating():
        entries = await sync_to_async(entries_for)(user)
        if not entries:  # the requests without a token of this server
            client = AnonymousClient()
            try:
                found = await estimate(repositories, client, anonymous=True)
                return found, [], client.requests
            finally:
                await client.close()
        pool = TokenPool(entries)
        try:
            return await estimate(repositories, pool), pool.entries, pool.points
        finally:
            await pool.close()

    return async_to_sync(estimating)()


__all__ = [
    "ASK_ABOVE",
    "ITEMS_PER_SECOND",
    "Estimate",
    "JobRunner",
    "Source",
    "cached_counts",
    "cancel",
    "claim_next",
    "completeness",
    "enqueue",
    "estimate",
    "estimate_for",
    "finish",
    "points_for",
    "requeue_stale",
    "run",
    "seconds_left",
    "seconds_per_point",
    "sources",
    "start_worker",
    "work",
    "work_async",
]
