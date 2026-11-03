"""The page of replies and its badges fetch what changed first, waiting a few seconds."""

from datetime import timedelta

import pytest
from django.utils import timezone

from community_insights import pipeline
from community_insights.models import FetchJob, Repository
from community_insights.pipeline.refresh import POLL

from ..data import replies_client
from ..factories import AccessTokenFactory, FetchJobFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def outdated(replied, monkeypatch):
    """o/r was read an hour ago; GitHub answers with the fake of the replies.

    Returns:
        The data of ``replied``.
    """
    Repository.objects.update(fetched_at=timezone.now() - timedelta(hours=1))
    monkeypatch.setattr("community_insights.github.Client", lambda token, *a, **k: replies_client())
    return replied


def repositories():
    """All repositories, as a page passes them.

    Returns:
        The query.
    """
    return Repository.objects.all()


def test_an_outdated_repository_is_fetched_with_the_tokens_of_the_owner(outdated):
    """The owner has a token: the fetch runs with it, and the page waited for it."""
    AccessTokenFactory(user=outdated["user"])
    assert pipeline.refresh(repositories(), outdated["user"], reason="test")
    job = FetchJob.objects.get()
    assert (job.user, job.status, job.reason) == (outdated["user"], FetchJob.DONE, "test")
    assert Repository.objects.get().fetched_at > timezone.now() - timedelta(minutes=1)


def test_visitors_use_the_shared_tokens(outdated):
    """A public page fetches with the points others share."""
    AccessTokenFactory(shared_percent=10)
    assert pipeline.refresh(repositories(), None, reason="test")
    assert FetchJob.objects.get().user is None


def test_without_tokens_nothing_is_fetched(outdated):
    """No token, nothing shared: the page shows itself at once."""
    assert not pipeline.refresh(repositories(), None, reason="test")
    assert not pipeline.refresh(repositories(), outdated["user"], reason="test")
    assert not FetchJob.objects.exists()


def test_without_points_left_nothing_is_fetched(outdated):
    """A token that used its points of this hour does not wait for a fetch."""
    token = AccessTokenFactory(user=outdated["user"], shared_percent=0)
    token.hour_started = timezone.now()
    token.used_in_hour = token.max_points
    token.save()
    assert not pipeline.refresh(repositories(), outdated["user"], reason="test")
    assert not FetchJob.objects.exists()


def test_fresh_and_never_read_repositories_are_not_fetched(replied):
    """Read a minute ago, or never: a never read one needs the page Fetch."""
    AccessTokenFactory(user=replied["user"])
    assert not pipeline.refresh(repositories(), replied["user"], reason="test")
    Repository.objects.update(fetched_at=None)
    assert not pipeline.refresh(repositories(), replied["user"], reason="test")
    assert not FetchJob.objects.exists()


def test_a_recent_job_is_not_repeated(outdated):
    """A job of the last minutes, also a failed one, is not queued again."""
    AccessTokenFactory(user=outdated["user"])
    FetchJobFactory(repository=outdated["repository"], status=FetchJob.FAILED)
    assert not pipeline.refresh(repositories(), outdated["user"], reason="test")
    assert FetchJob.objects.count() == 1


def test_a_timeout_of_0_turns_it_off(outdated, settings):
    """AUTO_FETCH_TIMEOUT=0: pages and badges never fetch."""
    AccessTokenFactory(user=outdated["user"])
    settings.AUTO_FETCH_TIMEOUT = 0
    assert not pipeline.refresh(repositories(), outdated["user"], reason="test")
    assert not FetchJob.objects.exists()


def test_the_page_waits_at_most_the_timeout(outdated, settings):
    """The worker is elsewhere and slow: after the timeout the page shows what is there."""
    AccessTokenFactory(user=outdated["user"])
    settings.FETCH_WORKER = "external-separate-container"  # nobody runs the job here
    times = iter([0.0, 0.5, 10.5])
    slept = []
    found = pipeline.refresh(
        repositories(),
        outdated["user"],
        reason="test",
        timeout=10,
        sleep=slept.append,
        clock=lambda: next(times),
    )
    assert not found
    assert slept == [POLL]
    assert FetchJob.objects.get().status == FetchJob.QUEUED, "it continues later"


def test_the_page_of_replies_fetches_first(outdated, signed_in):
    """The page reads what changed, then shows it."""
    AccessTokenFactory(user=outdated["user"])
    page = signed_in.get(f"/s/{outdated['project'].pk}/replies/").content.decode()
    assert "What changed on GitHub was read just now." in page
    assert FetchJob.objects.get().reason_url == f"/s/{outdated['project'].pk}/replies/"


def test_the_badge_of_a_project_fetches_with_the_tokens_of_its_owner(outdated, client):
    """The secret badge fetches with the tokens of whoever made the project."""
    AccessTokenFactory(user=outdated["user"])
    token = outdated["project"].badge_token
    assert client.get(f"/badge/{token}/replies/cid.svg").status_code == 200
    assert FetchJob.objects.get().user == outdated["user"]


def test_the_public_badge_fetches_with_the_shared_tokens(outdated, client):
    """The public badge fetches with the points others share, as a visitor."""
    AccessTokenFactory(shared_percent=10)
    assert client.get("/badge/s/o~r/replies/cid.svg").status_code == 200
    assert FetchJob.objects.get().user is None


def test_badges_wait_shorter_and_are_kept_an_hour(replied, client, monkeypatch, settings):
    """The image proxy of GitHub waits only seconds: badges wait AUTO_FETCH_BADGE_TIMEOUT."""
    waited = []
    monkeypatch.setattr(
        "community_insights.pipeline.refresh",
        lambda *args, timeout=None, **kwargs: waited.append(timeout),
    )
    settings.AUTO_FETCH_BADGE_TIMEOUT = 4
    response = client.get("/badge/s/o~r/replies/cid.svg")
    assert waited == [4]
    assert response["Cache-Control"] == "public, max-age=3600"
    page = client.get("/s/o~r/replies/cid/badge/").content.decode()
    assert "keep each badge for one hour" in page


def test_a_public_badge_reads_with_the_tokens_allowed_for_it(outdated, client):
    """A token allowed for the badges of the owner o: the badge of o~r fetches with it."""
    from community_insights.models import TokenGrant

    token = AccessTokenFactory(user=outdated["user"], shared_percent=0)
    TokenGrant.objects.create(token=token, kind=TokenGrant.BADGES, scope="o", percent=10)
    assert client.get("/badge/s/o~r/replies/cid.svg").status_code == 200
    job = FetchJob.objects.get()
    assert (job.user, job.use_kind, job.use_scope, job.use_login) == (None, "badges", "o~r", "cid")
    assert job.status == FetchJob.DONE
    assert token.grants.get().used_in_hour > 0, "the points of the grant were used"


def test_a_token_allowed_for_another_badge_does_not_update_this_one(outdated, client):
    """Allowed for the badge of ben only, and nothing shared: the badge of cid is not updated."""
    from community_insights.models import TokenGrant

    token = AccessTokenFactory(user=outdated["user"], shared_percent=0)
    TokenGrant.objects.create(
        token=token, kind=TokenGrant.BADGES, scope="o~r", login="ben", percent=10
    )
    client.get("/badge/s/o~r/replies/cid.svg")
    assert not FetchJob.objects.exists()
    client.get("/badge/s/o~r/replies/ben.svg")
    assert FetchJob.objects.get().use_login == "ben"


def test_public_pages_read_with_the_tokens_allowed_for_them(outdated, client):
    """A token allowed for the public pages of o~r: the page of replies fetches with it."""
    from community_insights.models import TokenGrant

    token = AccessTokenFactory(user=outdated["user"], shared_percent=0)
    TokenGrant.objects.create(token=token, kind=TokenGrant.PAGES, scope="o~r", percent=10)
    client.get("/s/o~r/replies/")
    job = FetchJob.objects.get()
    assert (job.use_kind, job.use_scope, job.status) == ("pages", "o~r", FetchJob.DONE)


def test_visitors_fetch_with_the_tokens_allowed_for_them(outdated, client):
    """Update of a visitor in o~r uses the grants for its visitors."""
    from community_insights.models import TokenGrant

    token = AccessTokenFactory(user=outdated["user"], shared_percent=0)
    TokenGrant.objects.create(token=token, kind=TokenGrant.VISITORS, scope="o~r", percent=10)
    client.post("/s/o~r/fetch/", {"action": "now", "next": "/s/o~r/"})
    job = FetchJob.objects.get()
    assert (job.user, job.use_kind, job.use_scope) == (None, "visitors", "o~r")
    assert job.status == FetchJob.DONE
