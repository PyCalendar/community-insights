"""Reading a real public repository with a real token: how many requests and
how long, and that reading it again asks almost nothing."""

import os

import pytest
from asgiref.sync import async_to_sync

from community_insights import github
from community_insights.models import Item
from community_insights.sync import Syncer, store_repository

from .conftest import real_token, wait_for_points

REPOSITORY = os.environ.get("PERFORMANCE_REPOSITORY", "niccokunzmann/open-web-calendar")

pytestmark = [
    pytest.mark.performance,
    pytest.mark.network,
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(real_token() is None, reason="needs $GITHUB_TOKEN or the old config"),
]


async def read(repository) -> tuple[int, str]:
    """Read a repository from GitHub; the requests and the summary."""
    client = github.Client(real_token())
    try:
        message = await Syncer(client).sync(repository)
        return client.requests, message
    finally:
        await client.close()


def test_reading_a_public_repository(timer):
    """Reading a public repository."""
    wait_for_points(real_token(), needed=200)
    repository = store_repository({"nameWithOwner": REPOSITORY})
    with timer(f"first read of {REPOSITORY}"):
        requests, message = async_to_sync(read)(repository)
    items = Item.objects.count()
    print(f"  {message}; {items} items with {requests} requests")
    assert items > 0
    assert requests <= items / 50 * 1.5 + 30, "about one request per 50 items"
    repository.refresh_from_db()
    with timer("second read"):
        again, message = async_to_sync(read)(repository)
    print(f"  {message} with {again} requests")
    assert again <= 4, "nothing changed: only the newest pages are asked"
