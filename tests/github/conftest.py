"""The tests of the GitHub client do not wait when it tries a request again."""

import pytest


@pytest.fixture(autouse=True)
def _no_waiting(monkeypatch):
    """Retries of the client happen at once; tests that check the waits note them themselves."""

    async def sleep(seconds):
        """Do not wait."""

    monkeypatch.setattr("community_insights.github.client.asyncio.sleep", sleep)
