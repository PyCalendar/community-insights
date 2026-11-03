"""Reading the commits, closers and approvals of pull requests read before these were read."""

import pytest
from asgiref.sync import async_to_sync

from community_insights import pipeline, stats
from community_insights.models import Event, FetchJob, Item
from community_insights.sync import Syncer

from ..data import replies_client
from ..factories import AccessTokenFactory
from ..fakes import FakeClient, item, node

pytestmark = pytest.mark.django_db


def old_pull_request():
    """bob's PR 12 as it is now on GitHub: an approval, a comment, closed by maint.

    Returns:
        The pull request as GitHub answers it.
    """
    return item(
        12,
        "bob",
        "2026-03-01T10:00:00Z",
        comments=[node("maint", "2026-03-01T12:00:00Z", "MEMBER")],
        reviews=[
            node("maint", "2026-03-01T11:00:00Z", "MEMBER", key="submittedAt", state="APPROVED")
        ],
        state="CLOSED",
        closer="maint",
        commits=[("bob", "2026-03-02T10:00:00Z")],
    )


def test_details_are_read_for_old_pull_requests(replied):
    """PR 12 was read before; the details are read with one request and complete it."""
    pr = Item.objects.get(number=12, kind=Item.PR)
    assert pr.details == 0 and stats.commits_unread(replied["project"].repositories.all()) == 1
    event = pr.events.create(actor="maint", kind=Event.REVIEW, at="2026-03-01T11:00:00Z")
    pr.state = "closed"
    pr.save()
    client = FakeClient(prs=[old_pull_request()])
    message = async_to_sync(Syncer(client).sync_details)(replied["repository"])
    assert message == "commits and closers of 1 of 1 pull requests read"
    assert client.requests == 1
    pr.refresh_from_db()
    event.refresh_from_db()
    assert (pr.details, pr.closed_by) == (Item.DETAILS, "maint")
    assert list(pr.commits.values_list("actor", flat=True)) == ["bob"]
    assert event.state == Event.APPROVED, "the approval is marked"
    assert stats.commits_unread(replied["project"].repositories.all()) == 0
    bob = stats.pull_replies(replied["project"].repositories.all(), login="bob")[0]
    assert bob.answered, "the commit after the comment replies to it"


def test_a_pull_request_github_no_longer_has(replied):
    """GitHub answers None for a deleted pull request: it is skipped."""
    message = async_to_sync(Syncer(FakeClient()).sync_details)(replied["repository"])
    assert message == "commits and closers of 0 of 1 pull requests read"


def test_the_details_cost_one_point_per_50(replied):
    """The estimate counts in the database: one request per 50 pull requests."""
    found = pipeline.details_estimates(replied["project"].repositories.all())
    assert [(e.repository.full_name, e.prs, e.points) for e in found] == [("o/r", 1, 1)]


def test_the_page_fetch_chooses_what_to_read(replied, signed_in, monkeypatch):
    """read=details shows the choice and the estimate without asking GitHub."""
    monkeypatch.setattr(
        "community_insights.pipeline.estimate_for",
        lambda *a: pytest.fail("GitHub is not asked for the details"),
    )
    page = signed_in.get(f"/s/{replied['project'].pk}/fetch/?read=details").content.decode()
    assert "The commits and closers of pull requests read before" in page
    assert 'name="read" value="details"' in page


def test_read_from_github_reads_at_once(replied, signed_in, monkeypatch):
    """The button queues the fetch without the page Fetch: here the details."""
    AccessTokenFactory(user=replied["user"])
    monkeypatch.setattr(
        "community_insights.github.Client",
        lambda token, *a, **k: FakeClient(prs=[old_pull_request()]),
    )
    pk = replied["project"].pk
    response = signed_in.post(
        f"/s/{pk}/fetch/", {"action": "now", "read": "details", "next": f"/s/{pk}/replies/"}
    )
    assert response.status_code == 302 and response["Location"] == f"/s/{pk}/replies/"
    job = FetchJob.objects.get()
    assert (job.what, job.status) == (FetchJob.DETAILS, FetchJob.DONE)
    assert Item.objects.get(number=12, kind=Item.PR).details == Item.DETAILS


def test_nothing_to_read(replied, signed_in):
    """Without old pull requests, the button says so."""
    Item.objects.update(details=Item.DETAILS)
    pk = replied["project"].pk
    response = signed_in.post(
        f"/s/{pk}/fetch/", {"action": "now", "read": "details", "next": f"/s/{pk}/"}, follow=True
    )
    assert b"Nothing to read." in response.content
    assert not FetchJob.objects.exists()


def test_the_button_has_a_menu(replied, signed_in):
    """Update reads at once all the pages need; its menu leads to the page Fetch."""
    pk = replied["project"].pk
    page = signed_in.get(f"/s/{pk}/replies/").content.decode()
    assert f'action="/s/{pk}/fetch/"' in page and 'name="action" value="now"' in page
    assert "Choose what and how much to read" in page
    assert 'name="read" value="details"' not in page, "a fetch reads the details anyway"


def test_reviews_are_read_with_their_state(replied):
    """The list of pull requests reads the state of each review."""
    assert set(Event.objects.filter(kind=Event.REVIEW).values_list("state", flat=True)) >= {
        "approved",
        "changes_requested",
        "commented",
    }
    assert Item.objects.get(number=1, kind=Item.PR).details == Item.DETAILS


def test_the_replies_client_is_complete():
    """Every pull request of the fake has an id, for the query of the details."""
    assert all(pr["id"] for pr in replies_client().prs)


def test_an_ordinary_fetch_also_reads_what_older_pull_requests_miss(
    replied, signed_in, monkeypatch
):
    """Update reads the changes and the commits and closers of old pull requests."""
    AccessTokenFactory(user=replied["user"])
    client = replies_client()
    client.prs[11] = old_pull_request()
    monkeypatch.setattr("community_insights.github.Client", lambda token, *a, **k: client)
    pk = replied["project"].pk
    signed_in.post(f"/s/{pk}/fetch/", {"action": "now", "next": f"/s/{pk}/"})
    job = FetchJob.objects.get()
    assert (job.what, job.status) == (FetchJob.CHANGES, FetchJob.DONE)
    assert "commits and closers of 1 of 1 pull requests read" in job.message
    assert not Item.objects.filter(kind=Item.PR, details__lt=Item.DETAILS).exists()


def test_the_estimate_counts_the_details(replied, signed_in, monkeypatch):
    """The page Fetch adds the requests for the details to the points of a fetch."""
    from community_insights.pipeline import Estimate

    def estimate_for(user, repositories, use=None):
        """No points for the changes, as if nothing changed."""
        return [Estimate(r, prs=1, issues=0, cached=1, points=0) for r in repositories], [], 0

    monkeypatch.setattr("community_insights.pipeline.estimate_for", estimate_for)
    page = signed_in.get(f"/s/{replied['project'].pk}/fetch/").content.decode()
    assert '<td class="text-end">1</td>\n  </tr>' in page, "one request for PR 12"
