"""The fetch page, the downloads page and the progress."""

import json

import pytest
from django.utils import timezone

from community_insights.models import AccessToken, FetchJob

from ..fakes import FakeClient, item

pytestmark = pytest.mark.django_db


def test_large_fetch_needs_a_limit(world, signed_in, monkeypatch):  # noqa: F811
    monkeypatch.setattr("community_insights.pipeline.ASK_ABOVE", 1)  # instead of 5000
    big = FakeClient(prs=[item(i, "a", "2026-01-01T00:00:00Z", reviews=[]) for i in range(1, 200)])
    monkeypatch.setattr("community_insights.github.Client", lambda token: big)
    pk = world["empty"].pk
    page = signed_in.get(f"/s/{pk}/fetch/")
    assert b"required" in page.content
    response = signed_in.post(f"/s/{pk}/fetch/", {"limit": ""}, follow=True)
    assert b"Please set a limit" in response.content
    assert not FetchJob.objects.filter(repository__full_name="o/empty").exists()


@pytest.mark.parametrize("limit", ["0", "-5", "many"])
def test_bad_limits(world, signed_in, monkeypatch, limit):  # noqa: F811
    monkeypatch.setattr("community_insights.github.Client", lambda token: FakeClient())
    response = signed_in.post(f"/s/{world['empty'].pk}/fetch/", {"limit": limit}, follow=True)
    assert b"whole number" in response.content


def test_fetch_does_not_redirect_to_other_sites(world, signed_in, monkeypatch, settings):  # noqa: F811
    settings.FETCH_WORKER = "external-separate-container"
    monkeypatch.setattr("community_insights.github.Client", lambda token: FakeClient())
    pk = world["empty"].pk
    response = signed_in.post(f"/s/{pk}/fetch/", {"next": "https://evil.example/"})
    assert response["Location"] == f"/s/{pk}/"


def test_priority_is_limited_and_jobs_reordered(world, signed_in, monkeypatch, settings):  # noqa: F811
    settings.FETCH_WORKER = "external-separate-container"
    monkeypatch.setattr("community_insights.github.Client", lambda token: FakeClient())
    signed_in.post(f"/s/{world['empty'].pk}/fetch/", {"priority": "999999"})
    job = FetchJob.objects.get(repository__full_name="o/empty", status="queued")
    assert job.priority == FetchJob.HIGH and job.reason == "Statistics of o/empty"
    first = FetchJob.objects.filter(status="queued").order_by("-priority", "created").first()
    other = FetchJob.objects.filter(status="queued").exclude(pk=first.pk).first()
    signed_in.post("/dashboard/downloads/", {"id": other.pk, "action": "up"})
    assert (
        FetchJob.objects.filter(status="queued").order_by("-priority", "created").first().pk
        == other.pk
    )


def test_downloads_page_shows_running_and_queued_with_reasons(world, signed_in):  # noqa: F811
    response = signed_in.get("/dashboard/downloads/")
    for text in [b"test running", b"test queued", b"test done", b"Cancel"]:
        assert text in response.content


def test_cancel_running_job_from_the_page(world, signed_in):  # noqa: F811
    job = FetchJob.objects.get(status="running")
    signed_in.post("/dashboard/downloads/", {"id": job.pk, "action": "cancel"})
    job.refresh_from_db()
    assert job.cancel_requested and job.status == "running"  # stops after its request


def test_progress_json(world, signed_in):  # noqa: F811
    data = json.loads(signed_in.get(f"/s/{world['project'].pk}/progress.json").content)
    assert {"percent", "items", "total", "seconds_left", "jobs"} <= set(data)
    assert {j["status"] for j in data["jobs"]} == {"queued", "running"}


def test_fetch_warns_when_the_points_of_the_hour_are_not_enough(world, signed_in, monkeypatch):  # noqa: F811
    from community_insights.models import Profile

    big = FakeClient(prs=[item(i, "a", "2026-01-01T00:00:00Z", reviews=[]) for i in range(1, 400)])
    monkeypatch.setattr("community_insights.github.Client", lambda token: big)
    # no linked account: only the own token, with 5 points per hour
    from allauth.socialaccount.models import SocialToken

    SocialToken.objects.all().delete()
    AccessToken.objects.update(rate_limit=100, max_percent=5)
    pk = world["empty"].pk
    page = signed_in.get(f"/s/{pk}/fetch/").content.decode()
    assert "The limit of your tokens for this hour is reached" in page
    response = signed_in.post(f"/s/{pk}/fetch/", {"action": "allow", "extra": "20"}, follow=True)
    assert b"20 more points" in response.content
    assert Profile.of(world["user"]).extra_left(timezone.now()) == 20
    bad = signed_in.post(f"/s/{pk}/fetch/", {"action": "allow", "extra": "-3"}, follow=True)
    assert b"Invalid number of points" in bad.content
