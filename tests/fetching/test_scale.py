"""Edge cases of size and of things happening at the same time."""

import pytest

from community_insights import pipeline
from community_insights.models import Event, FetchJob, Person, Project
from community_insights.sync import add_project, read_repository, store_repository

from ..fakes import FakeClient, item, node, repo, run

pytestmark = pytest.mark.django_db


def test_reviews_on_more_pages(db):
    """Reviews on more pages."""
    pr = item(
        1,
        "a",
        "2026-01-01T00:00:00Z",
        reviews=[node("r1", "2026-01-01T01:00:00Z", key="submittedAt")],
    )
    pr["reviews"]["pageInfo"] = {"hasNextPage": True, "endCursor": "c"}
    client = FakeClient(prs=[pr])
    client.more = {("id1", "reviews"): [node("r2", "2026-01-02T00:00:00Z", key="submittedAt")]}
    read_repository(client, store_repository(repo("o/r")))
    reviewers = sorted(Event.objects.filter(kind="review").values_list("actor", flat=True))
    assert reviewers == ["r1", "r2"]


def test_more_people_than_one_batch(db):
    """More people than one batch."""
    commenters = [node(f"p{i}", "2026-01-02T00:00:00Z") for i in range(35)]
    client = FakeClient(
        issues=[item(1, "a", "2026-01-01T00:00:00Z", comments=commenters)],
        people={f"p{i}": {"name": f"P {i}", "location": "", "avatarUrl": ""} for i in range(35)},
    )
    before = client.requests
    read_repository(client, store_repository(repo("o/r")))
    assert Person.objects.filter(name__startswith="P ").count() == 35
    people_requests = client.requests - before - 3  # pull requests, issues, commits
    assert people_requests == 2, "36 people in batches of 30: two requests"


def test_an_organisation_with_hundreds_of_repositories(user):  # noqa: F811
    """An organisation with hundreds of repositories."""
    client = FakeClient(repositories=[repo(f"big/r{i}", i) for i in range(250)])
    project = run(add_project, user, client, "big")
    assert project.repositories.count() == 250
    before = client.requests
    estimates = run(pipeline.estimate, project.repositories.all(), client)
    assert len(estimates) == 250
    assert client.requests - before == 5, "totals of 50 repositories in one request"
    again = client.requests
    run(pipeline.estimate, project.repositories.all(), client)
    assert client.requests == again, "the totals are kept for some minutes"


def test_two_workers_cannot_take_the_same_job(user):  # noqa: F811
    """Two workers cannot take the same job."""
    job = FetchJob.objects.create(user=user, repository=store_repository(repo("o/r")))
    first = pipeline.claim_next()
    assert first.pk == job.pk and first.status == FetchJob.RUNNING
    assert pipeline.claim_next() is None, "the second worker finds nothing"
    # a worker that read the job as queued before the other took it does not get it
    assert FetchJob.objects.filter(pk=job.pk, status=FetchJob.QUEUED).update(status="running") == 0


def test_several_jobs_at_the_same_time(user, settings):  # noqa: F811
    """Several jobs at the same time."""
    from community_insights.models import AccessToken

    AccessToken.objects.create(user=user, token="t", login="x")
    settings.FETCH_CONCURRENCY = 3
    for name in ("o/a", "o/b", "o/c", "o/d"):
        FetchJob.objects.create(user=user, repository=store_repository(repo(name)))
    client = FakeClient(issues=[item(1, "a", "2026-01-01T00:00:00Z")])
    assert pipeline.work(once=True, make_client=lambda token: client) == 4
    assert set(FetchJob.objects.values_list("status", flat=True)) == {FetchJob.DONE}
    assert Project.objects.count() == 0  # jobs need no project
