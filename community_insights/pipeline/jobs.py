"""The queue of fetch jobs: adding, taking the next, cancelling, finishing."""

import math
from datetime import datetime, timedelta

from django.db.models import Q
from django.utils import timezone

from .. import errors
from ..models import FetchJob


def enqueue(
    user, estimates, *, priority=FetchJob.NORMAL, point_limit=None, reason="", reason_url=""
) -> list[FetchJob]:
    """Queue a job per repository, unless one is queued or running, and start the worker.

    A limit of points is shared in proportion to the estimates.

    Args:
        user: Whose tokens read; None for a visitor, who uses the donated ones.
        estimates: The estimate of each repository.
        priority: The priority of the jobs, higher first.
        point_limit: The most points all jobs together may use, None for no limit.
        reason: Why the jobs run, shown on the page Downloads.
        reason_url: The page they were started from.

    Returns:
        The jobs queued; repositories with a job queued or running get none.
    """
    from .worker import start_worker

    jobs = []
    planned = sum(e.points for e in estimates) or 1
    for e in estimates:
        if FetchJob.objects.filter(repository=e.repository, status__in=FetchJob.ACTIVE).exists():
            continue
        limit = None
        if point_limit is not None:
            limit = max(1, math.floor(point_limit * e.points / planned))
        jobs.append(
            FetchJob.objects.create(
                user=user,
                repository=e.repository,
                priority=priority,
                point_limit=limit,
                points_estimated=e.points,
                items_expected=max(e.missing, 0) or e.items,
                reason=reason[:300],
                reason_url=reason_url[:300],
            )
        )
    start_worker()
    return jobs


def claim_next() -> FetchJob | None:
    """The queued job with the highest priority, marked as running.

    The update only succeeds for one worker, so several workers can take jobs at once.

    Returns:
        The job, None if no job can start now.
    """
    now = timezone.now()
    queued = FetchJob.objects.filter(status=FetchJob.QUEUED).filter(
        Q(not_before__isnull=True) | Q(not_before__lte=now)
    )
    for job in queued.order_by("-priority", "created")[:10]:
        if FetchJob.objects.filter(pk=job.pk, status=FetchJob.QUEUED).update(
            status=FetchJob.RUNNING, started=job.started or now
        ):
            # with what the async runner needs, so it does not ask the database
            return FetchJob.objects.select_related("repository", "user").get(pk=job.pk)
    return None


def has_ready_jobs() -> bool:
    """Whether a queued job can start now.

    Returns:
        True if a queued job does not wait for a rate limit.
    """
    return (
        FetchJob.objects.filter(status=FetchJob.QUEUED)
        .filter(Q(not_before__isnull=True) | Q(not_before__lte=timezone.now()))
        .exists()
    )


def next_waiting() -> datetime | None:
    """When the first queued job that waits for a rate limit may start.

    Returns:
        The time, None if no job waits.
    """
    return (
        FetchJob.objects.filter(status=FetchJob.QUEUED, not_before__isnull=False)
        .order_by("not_before")
        .values_list("not_before", flat=True)
        .first()
    )


def finish(job: FetchJob, status: str, outcome) -> FetchJob:
    """End a job with a message, or with an error of errors/.

    Args:
        job: The job.
        status: The status it ends with, such as ``done`` or ``failed``.
        outcome: The message, or the error it stopped with.

    Returns:
        The job, saved.
    """
    job.status, job.finished = status, timezone.now()
    job.message = str(outcome)
    job.error_code = outcome.code if isinstance(outcome, errors.CommunityError) else ""
    if status == FetchJob.DONE:
        job.items_expected = max(job.items_expected, job.items_done)
    job.save()
    return job


def wait(job: FetchJob, error: errors.AllTokensUsedUp) -> FetchJob:
    """Put a job back into the queue until the tokens can be used again.

    Args:
        job: The job.
        error: The error that says when the tokens can be used again.

    Returns:
        The job, saved.
    """
    job.status, job.not_before = FetchJob.QUEUED, error.reset_at
    job.message, job.error_code = str(error), error.code
    job.save()
    return job


def cancel(job: FetchJob) -> None:
    """Stop a job: a queued one at once, a running one after its current request.

    Args:
        job: The job.
    """
    if job.status == FetchJob.QUEUED:
        finish(job, FetchJob.CANCELLED, errors.FetchCancelled("Cancelled before it started."))
    elif job.status == FetchJob.RUNNING:
        FetchJob.objects.filter(pk=job.pk).update(cancel_requested=True)


def cancel_requested(job: FetchJob) -> bool:
    """Whether somebody cancelled the job while it runs.

    Args:
        job: The running job.

    Returns:
        True if it was cancelled.
    """
    return FetchJob.objects.filter(pk=job.pk, cancel_requested=True).exists()


def requeue_stale(after: timedelta = timedelta(hours=1)) -> int:
    """Jobs left running by a stopped process go back to the queue.

    Args:
        after: How long a job may run before it counts as left behind.

    Returns:
        How many jobs were queued again.
    """
    limit = timezone.now() - after
    return FetchJob.objects.filter(status=FetchJob.RUNNING, started__lt=limit).update(
        status=FetchJob.QUEUED
    )
