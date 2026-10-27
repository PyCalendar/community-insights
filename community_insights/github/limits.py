"""Limits of the requests to GitHub besides the hourly points.

Limits of the requests to GitHub besides the hourly points: the secondary rate limits of GitHub (at
most 100 requests at the same time, 2000 GraphQL points per minute) and a cap for this server, as
all tokens share its IP.
"""

import asyncio
import weakref

from django.conf import settings

PER_TOKEN = 10  # requests of one token at the same time
POINTS_PER_SECOND = 30  # below 2000 points per minute
MAX_WAIT = 60  # seconds: waiting longer for retry-after hands over to the next token
RETRIES = 3

_server: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


def server_slots() -> asyncio.Semaphore:
    """Requests of this process at the same time, for the running event loop.

    Returns:
        The semaphore of the running event loop.
    """
    loop = asyncio.get_running_loop()
    if loop not in _server:
        _server[loop] = asyncio.Semaphore(getattr(settings, "GITHUB_MAX_CONCURRENT", 20))
    return _server[loop]


def backoff(attempt: int, retry_after: float | None) -> float:
    """Seconds to wait before the next try: what GitHub asked, or 1, 2, 4...

    Args:
        attempt: How many tries failed before, from 0.
        retry_after: The seconds GitHub asked to wait, None if it did not say.

    Returns:
        The seconds.
    """
    return retry_after if retry_after is not None else 2**attempt
