"""Whether a pull request is a draft is read from GitHub, also for those read before."""

import pytest
from asgiref.sync import async_to_sync

from community_insights.models import Item
from community_insights.sync import Syncer, store_repository
from community_insights.sync.queries import details_query, list_query
from community_insights.sync.sources import AnonymousSource

from ..fakes import FakeClient, item, repo, run
from ..fakes.rest import FakeREST, rest_issue

pytestmark = pytest.mark.django_db


def draft_pull(number=7, state="OPEN"):
    """An open pull request that is a draft, as GitHub answers it.

    Args:
        number: Its number.
        state: ``OPEN`` or ``CLOSED``.

    Returns:
        The pull request.
    """
    data = item(
        number,
        "kim",
        "2026-01-05T10:00:00Z",
        reviews=[],
        state=state,
        commits=[("kim", "2026-01-05T09:00:00Z")],
    )
    data["isDraft"] = True
    return data


def test_the_queries_ask_for_it():
    """The list of pull requests and their details ask GitHub for isDraft."""
    assert "isDraft" in list_query(Item.PR)
    assert "isDraft" not in list_query(Item.ISSUE), "issues have no drafts"
    assert "isDraft" in details_query()


def test_a_draft_is_stored(db):
    """A pull request read as a draft is one; others are not."""
    repository = store_repository(repo("o/r"))
    ready = item(8, "lea", "2026-01-05T11:00:00Z", reviews=[])
    run(Syncer(FakeClient(prs=[draft_pull(), ready])).sync, repository)
    assert set(Item.objects.values_list("number", "draft")) == {(7, True), (8, False)}


def test_the_details_read_it_for_pull_requests_read_before(db):
    """Read before drafts were known (details 1): the details mark it."""
    repository = store_repository(repo("o/r"))
    run(Syncer(FakeClient(prs=[draft_pull()])).sync, repository)
    Item.objects.update(draft=False, details=1)
    async_to_sync(Syncer(FakeClient(prs=[draft_pull()])).sync_details)(repository)
    pr = Item.objects.get()
    assert (pr.draft, pr.details) == (True, Item.DETAILS)


def test_without_a_token_the_rest_api_says_it(db):
    """The REST API marks drafts with "draft"."""
    repository = store_repository(repo("o/r"))
    issue = rest_issue(3, "kim", "2026-01-05T10:00:00Z", pull=True)
    issue["draft"] = True
    run(Syncer(AnonymousSource(FakeREST(issues=[issue]))).sync, repository)
    assert Item.objects.get(number=3).draft
