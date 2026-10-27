"""A stopped fetch continues where it stopped."""

import pytest

from community_insights.models import Item
from community_insights.sync import store_repository

from ..fakes import FakeClient, item, repo, run

pytestmark = pytest.mark.django_db


class Paged(FakeClient):
    """Gives the pull requests in pages of 2, and can stop after some pages."""

    def __init__(self, stop_after=None, **kwargs):
        """A fake client that stops after some pages."""
        super().__init__(**kwargs)
        self.pages, self.stop_after = [], stop_after

    async def graphql(self, query, **variables):
        """Note the pages of pull requests, and stop after the number given."""
        if "pullRequests(" not in query:
            return await super().graphql(query, **variables)
        if self.stop_after is not None and len(self.pages) == self.stop_after:
            raise RuntimeError("stopped")
        self.pages.append(variables.get("after"))
        items = sorted(self.prs, key=lambda i: i["updatedAt"], reverse=True)
        start = int(variables.get("after") or 0)
        part = items[start : start + 2]
        more = start + 2 < len(items)
        return {
            "repository": {
                "pullRequests": {
                    "nodes": part,
                    "totalCount": len(items),
                    "pageInfo": {"hasNextPage": more, "endCursor": str(start + 2)},
                }
            }
        }


def test_a_stopped_fetch_continues_where_it_stopped(user):  # noqa: F811
    """A stopped fetch continues where it stopped."""
    from community_insights.sync import Syncer

    prs = [item(i, "a", f"2026-01-{i:02d}T00:00:00Z", reviews=[]) for i in range(1, 7)]
    repository = store_repository(repo("o/r"))
    first = Paged(stop_after=2, prs=prs)
    with pytest.raises(RuntimeError):
        run(Syncer(first).sync, repository)
    assert Item.objects.count() == 4 and first.pages == [None, "2"]
    repository.refresh_from_db()
    assert repository.resume["pr"]["cursor"] == "4"
    second = Paged(prs=prs)
    run(Syncer(second).sync, repository)
    assert second.pages == ["4"], "only the rest is read"
    assert Item.objects.filter(kind="pr").count() == 6
    repository.refresh_from_db()
    assert repository.resume == {} and repository.prs_synced_until is not None
