"""The queue of fetch jobs: priorities, running, cancelling, limits."""

from datetime import timedelta

import pytest
from asgiref.sync import sync_to_async
from django.utils import timezone

from community_insights import pipeline
from community_insights.github import RateLimited
from community_insights.models import Event, FetchJob, Item, Person
from community_insights.sync import store_repository
from tests.factories import AccessTokenFactory, FetchJobFactory

from ..data import full_client
from ..fakes import Counting, FakeClient, item, node, repo

pytestmark = pytest.mark.django_db


def run_with(client, job):
    """Run a job with a fake client."""
    return pipeline.run(job, make_client=lambda token: client)


@pytest.fixture
def with_token(user):  # noqa: F811
    """The user with a token."""
    AccessTokenFactory(user=user)
    return user


def test_claim_takes_the_highest_priority_first(user):  # noqa: F811
    """Claim takes the highest priority first."""
    low = FetchJobFactory(user=user, repository__full_name="o/low", priority=FetchJob.LOW)
    high = FetchJobFactory(user=user, repository__full_name="o/high", priority=FetchJob.HIGH)
    assert pipeline.claim_next().pk == high.pk
    assert pipeline.claim_next().pk == low.pk
    assert pipeline.claim_next() is None


def test_claim_waits_for_not_before(user):  # noqa: F811
    """Claim waits for not before."""
    FetchJobFactory(
        user=user, repository__full_name="o/r", not_before=timezone.now() + timedelta(minutes=5)
    )
    assert pipeline.claim_next() is None


def test_enqueue_does_not_queue_twice_and_shares_the_limit(user, settings):  # noqa: F811
    """Enqueue does not queue twice and shares the limit."""
    settings.FETCH_WORKER = "external-separate-container"
    a, b = store_repository(repo("o/a")), store_repository(repo("o/b"))
    estimates = [pipeline.Estimate(a, 1, 1, 0, 30), pipeline.Estimate(b, 1, 1, 0, 10)]
    jobs = pipeline.enqueue(user, estimates, point_limit=20, reason="r")
    assert [j.point_limit for j in jobs] == [15, 5]
    assert pipeline.enqueue(user, estimates) == []


def test_run_reads_and_counts(with_token):
    """Run reads and counts."""
    job = FetchJobFactory(user=with_token, repository__full_name="o/r", items_expected=5)
    FetchJob.objects.filter(pk=job.pk).update(status=FetchJob.RUNNING)
    job = run_with(full_client(), job)
    assert job.status == FetchJob.DONE, job.message
    assert job.items_done == 5 and job.points_used > 0 and job.percent == 100


def test_cancel_a_running_job_keeps_what_was_read(with_token):
    """Cancel a running job keeps what was read."""
    job = FetchJobFactory(user=with_token, repository__full_name="o/r")
    client = full_client()
    original = client.graphql

    async def cancel_after_first_page(query, **variables):
        """Answer, then cancel the job."""
        result = await original(query, **variables)
        await sync_to_async(FetchJob.objects.filter(pk=job.pk).update)(cancel_requested=True)
        return result

    client.graphql = cancel_after_first_page
    job = run_with(client, job)
    assert job.status == FetchJob.CANCELLED and job.error_code == "FetchCancelled"
    # both kinds are read at the same time: their first pages are kept
    assert Item.objects.filter(kind="pr").count() == 3
    # bots are known without asking; the people were not read from GitHub any more
    assert not Person.objects.filter(is_bot=False).exists()


def test_cancel_a_queued_job(with_token):
    """Cancel a queued job."""
    job = FetchJobFactory(user=with_token, repository__full_name="o/r")
    pipeline.cancel(job)
    job.refresh_from_db()
    assert job.status == FetchJob.CANCELLED and job.finished


def test_limit_stops_and_keeps_the_data(with_token):
    """Limit stops and keeps the data."""
    job = FetchJobFactory(user=with_token, repository__full_name="o/r", point_limit=1)
    job = run_with(full_client(), job)
    assert job.status == FetchJob.LIMIT and job.error_code == "FetchLimitReached"
    assert Item.objects.count() == 3


def test_rate_limit_puts_the_job_back_to_wait(with_token):
    """Rate limit puts the job back to wait."""
    reset = timezone.now() + timedelta(minutes=20)
    job = run_with(
        Counting("x", fail=RateLimited("used", reset)),
        FetchJobFactory(user=with_token, repository__full_name="o/r"),
    )
    assert job.status == FetchJob.QUEUED and job.not_before == reset


def test_a_failing_fetch_is_reported(with_token):
    """A failing fetch is reported."""
    job = run_with(
        Counting("x", fail=RuntimeError("boom")),
        FetchJobFactory(user=with_token, repository__full_name="o/r"),
    )
    # an unknown error is translated: shown as a bug to report, with its text
    assert job.status == FetchJob.FAILED and job.error_code == "UnexpectedError"
    assert job.message == "RuntimeError: boom"


def test_without_any_token_the_job_reads_without_a_token(user, monkeypatch):  # noqa: F811
    """Without any token the job reads without a token."""
    from ..fakes.rest import FakeREST

    monkeypatch.setattr("community_insights.pipeline.runner.AnonymousClient", FakeREST)
    job = pipeline.run(FetchJobFactory(user=user, repository__full_name="o/r"))
    assert job.status == FetchJob.DONE and job.points_used == 4


def test_comments_on_more_pages_are_read(with_token):
    """Comments on more pages are read."""
    big = item(1, "a", "2026-01-01T00:00:00Z", comments=[node("b", "2026-01-01T01:00:00Z")])
    big["comments"]["pageInfo"] = {"hasNextPage": True, "endCursor": "c1"}
    client = FakeClient(issues=[big])
    client.more = {("id1", "comments"): [node("c", "2026-01-02T00:00:00Z")]}
    run_with(client, FetchJobFactory(user=with_token, repository__full_name="o/r"))
    assert sorted(Event.objects.filter(kind="comment").values_list("actor", flat=True)) == [
        "b",
        "c",
    ]


def test_requeue_stale_running_jobs(user):  # noqa: F811
    """Requeue stale running jobs."""
    job = FetchJobFactory(
        user=user,
        repository__full_name="o/r",
        status=FetchJob.RUNNING,
        started=timezone.now() - timedelta(hours=2),
    )
    assert pipeline.requeue_stale() == 1
    job.refresh_from_db()
    assert job.status == FetchJob.QUEUED


def test_the_thread_waits_for_jobs_that_wait_for_a_rate_limit(user, monkeypatch):  # noqa: F811
    """A job waiting for the reset of a rate limit is not forgotten."""
    from community_insights.pipeline import worker

    job = FetchJobFactory(
        user=user, repository__full_name="o/r", not_before=timezone.now() + timedelta(seconds=30)
    )
    slept = []

    def sleep(seconds):
        """Note the wait; the job ran meanwhile."""
        slept.append(seconds)
        FetchJob.objects.filter(pk=job.pk).update(status=FetchJob.DONE)  # it ran meanwhile

    monkeypatch.setattr(worker.time, "sleep", sleep)
    monkeypatch.setattr(worker.connections, "close_all", lambda: None)
    worker._thread_main()
    assert len(slept) == 1 and 25 <= slept[0] <= 30
    assert pipeline.jobs.next_waiting() is None
