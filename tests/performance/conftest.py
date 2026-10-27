import os
import re
import time
from contextlib import contextmanager
from pathlib import Path

import pytest

CONFIG = Path.home() / ".config" / "gh-community" / "config.yaml"


def real_token() -> str | None:
    """$GITHUB_TOKEN, or the token of the configuration of the old command
    line tool. It is never printed."""
    if os.environ.get("GITHUB_TOKEN"):
        return os.environ["GITHUB_TOKEN"]
    if CONFIG.exists():
        found = re.search(r"^token:\s*['\"]?([^'\"\s#]+)", CONFIG.read_text(), re.M)
        if found:
            return found.group(1)
    return None


class Timer:
    """Measures and prints how long named steps take."""

    def __init__(self):
        self.times: dict[str, float] = {}

    @contextmanager
    def __call__(self, name):
        start = time.perf_counter()
        yield
        self.times[name] = time.perf_counter() - start
        print(f"  {name}: {self.times[name]:.3f} s")


@pytest.fixture
def timer():
    return Timer()


WAIT = 600  # seconds between looks at the rate limit, like the check of the disk


def points_left(token: str) -> int:
    from asgiref.sync import async_to_sync

    from community_insights import github

    async def ask():
        client = github.Client(token)
        try:
            return (await client.graphql("query { rateLimit { remaining } }"))["rateLimit"]
        finally:
            await client.close()

    return async_to_sync(ask)()["remaining"]


def wait_for_points(token: str, needed: int) -> None:
    """Do not fail for a low rate limit: wait 10 minutes and look again."""
    while (left := points_left(token)) < needed:
        print(f"  {left} points left, {needed} needed: waiting {WAIT // 60} minutes")
        time.sleep(WAIT)
