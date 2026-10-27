"""How complete the data of repositories is and when it will be."""

from dataclasses import dataclass

from django.utils import timezone

from ..models import FetchJob, Repository
from .estimate import cached_counts

ITEMS_PER_SECOND = 20.0  # until measured


@dataclass
class Source:
    """A repository of a page with its items read and on GitHub."""

    repository: Repository
    prs: int
    issues: int
    prs_total: int | None
    issues_total: int | None

    @property
    def total(self) -> int | None:
        """Pull requests and issues on GitHub; None while unknown."""
        if self.prs_total is None or self.issues_total is None:
            return None
        return self.prs_total + self.issues_total

    @property
    def percent(self) -> int:
        """How much of the items is read, 0 to 100."""
        if self.total is None:
            read = self.repository.prs_synced_until and self.repository.issues_synced_until
            return 100 if read and not (self.prs or self.issues) else 0
        if self.total == 0:
            return 100
        return min(100, round(100 * (self.prs + self.issues) / self.total))


def sources(repositories) -> list[Source]:
    """The sources of a page, with the items read of each."""
    cached = cached_counts(repositories)
    return [
        Source(
            r,
            cached.get(r.pk, {}).get("prs", 0),
            cached.get(r.pk, {}).get("issues", 0),
            r.prs_total,
            r.issues_total,
        )
        for r in repositories
    ]


def completeness(repositories) -> dict:
    """How complete the data of the repositories is.

    How complete the data of the repositories is, the active jobs and the estimated seconds
    until all is read.
    """
    found = sources(repositories)
    have = sum(s.prs + s.issues for s in found)
    known = [s for s in found if s.total is not None]
    total = sum(s.total for s in found if s.total is not None)
    if not found:
        percent = 100
    elif len(known) < len(found):
        percent = round(sum(s.percent for s in found) / len(found))
    else:
        percent = 100 if total == 0 else min(100, round(100 * have / total))
    jobs = list(
        FetchJob.objects.filter(repository__in=repositories, status__in=FetchJob.ACTIVE)
        .select_related("repository")
        .order_by("-priority", "created")
    )
    return {
        "percent": percent,
        "items": have,
        "total": total if len(known) == len(found) else None,
        "sources": found,
        "jobs": jobs,
        "seconds_left": seconds_left(jobs),
    }


def items_per_second(jobs) -> float:
    """How fast items are read now, from a running job, else as measured before."""
    for job in jobs:
        if job.status == FetchJob.RUNNING and job.started and job.items_done >= 50:
            elapsed = (timezone.now() - job.started).total_seconds()
            if elapsed > 0:
                return job.items_done / elapsed
    return ITEMS_PER_SECOND


def seconds_left(jobs) -> float | None:
    """Until the active jobs are done; None without active jobs."""
    if not jobs:
        return None
    rate = items_per_second(jobs)
    remaining = sum(max(0, j.items_expected - j.items_done) for j in jobs)
    wait = max(
        ((j.not_before - timezone.now()).total_seconds() for j in jobs if j.not_before),
        default=0,
    )
    return max(0.0, wait) + remaining / rate
