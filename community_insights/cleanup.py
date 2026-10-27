"""Keeping the database small.

Keeping the database small: deleting what nobody used for a long time, at most once a day, and what
was used longest ago when the database is bigger than DATABASE_MAX_MB; data younger than
DATABASE_MIN_AGE_HOURS stays.
"""

import logging
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.db.models import Q
from django.utils import timezone

from .models import Event, FetchJob, Person, Repository

LAST_CLEANUP = "community:last-cleanup"
LAST_SHRINK = "community:last-shrink"  # the report of the last check of the size
BLOCKED_UNTIL = "community:shrink-blocked-until"  # only young data was left
HEADROOM = 0.1  # shrink to 10 % below the limit, so it is not needed again at once
MB = 1024 * 1024
BATCH = 5  # repositories deleted before the size is measured again

log = logging.getLogger(__name__)


def clear_unused(days: int) -> tuple[int, int]:
    """Delete the repositories and people not used for some days.

    Delete the repositories and people not used for `days` days; their projects stay and read
    them again when needed. (repositories, people)

    Args:
        days: How many days without use.

    Returns:
        How many repositories and people were deleted.
    """
    limit = timezone.now() - timedelta(days=days)
    repositories = Repository.objects.filter(last_used_at__lt=limit)
    people = Person.objects.filter(last_used_at__lt=limit)
    counts = repositories.count(), people.count()
    repositories.delete()
    people.delete()
    return counts


def clean_up_daily() -> tuple[int, int] | None:
    """clear_unused(CACHE_KEEP_DAYS) if it did not run in the last day; None if it did not run.

    CACHE_KEEP_DAYS = 0 keeps everything.

    Returns:
        The repositories and people deleted, or None.
    """
    from . import documents

    documents.clean_up()
    days = getattr(settings, "CACHE_KEEP_DAYS", 90)
    if not days or not cache.add(LAST_CLEANUP, timezone.now().isoformat(), timeout=24 * 3600):
        return None
    return clear_unused(days)


def _number(cursor, sql: str) -> int:
    """The number a query of one value answers.

    Args:
        cursor: An open cursor of the database.
        sql: A query that answers one row with one number, such as a PRAGMA.

    Returns:
        The number.
    """
    cursor.execute(sql)
    row = cursor.fetchone()
    assert row is not None, sql  # these queries always answer one row
    return row[0]


def database_size() -> int | None:
    """The size of the database files in bytes; None if it cannot be measured.

    Returns:
        The bytes, or None for other databases than SQLite and PostgreSQL.
    """
    vendor = connection.vendor
    if vendor == "sqlite":
        name = Path(str(connection.settings_dict["NAME"]))
        files = [name, name.with_name(name.name + "-wal")]
        return sum(f.stat().st_size for f in files if f.exists()) if name.exists() else None
    if vendor == "postgresql":
        with connection.cursor() as cursor:
            return _number(cursor, "SELECT pg_database_size(current_database())")
    return None


def database_used() -> int | None:
    """The bytes the data uses, without compacting.

    The bytes the data uses: what the database will have after compacting, measured without
    compacting (SQLite: pages without the free ones).

    Returns:
        The bytes, or None if they cannot be measured.
    """
    if connection.vendor != "sqlite":
        return database_size()
    with connection.cursor() as cursor:
        pages = _number(cursor, "PRAGMA page_count")
        free = _number(cursor, "PRAGMA freelist_count")
        return (pages - free) * _number(cursor, "PRAGMA page_size")


def compact() -> None:
    """Give the space of deleted rows back (VACUUM); not inside a transaction."""
    with connection.cursor() as cursor:
        cursor.execute("VACUUM")
        if connection.vendor == "sqlite":
            cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")


@dataclass
class ShrinkReport:
    """What a check of the size did: the sizes, what was deleted and whether it fits now.

    Attributes:
        before: The bytes the data used before.
        after: The bytes it uses now.
        limit: The bytes it is kept below.
        repositories: How many repositories were deleted.
        people: How many people were deleted.
        enough: Whether it fits below the limit now.
    """

    before: int
    after: int
    limit: int
    repositories: int = 0
    people: int = 0
    enough: bool = True  # False: only data younger than the minimum age is left

    def as_dict(self) -> dict:
        """The report for the cache and the cache page, sizes in MB.

        Returns:
            When it was checked, the sizes before, after and of the limit, what was deleted
            and whether that was enough.
        """
        return {
            "checked": timezone.now().isoformat(),
            "before_mb": round(self.before / MB, 1),
            "after_mb": round(self.after / MB, 1),
            "limit_mb": round(self.limit / MB, 1),
            "repositories": self.repositories,
            "people": self.people,
            "enough": self.enough,
        }


def young_since(now):
    """The time after which data is too young to be deleted for space.

    Args:
        now: The time now.

    Returns:
        The time: data used or read after it is kept.
    """
    return now - timedelta(hours=getattr(settings, "DATABASE_MIN_AGE_HOURS", 24))


def removable(now) -> tuple:
    """What may be deleted to save space.

    What may be deleted to save space: used and read before the minimum age, and no fetch of it
    queued or running. (repositories, people)

    Args:
        now: The time now.

    Returns:
        The repositories and the people, as queries, used longest ago first.
    """
    young = young_since(now)
    busy = FetchJob.objects.filter(status__in=FetchJob.ACTIVE).values("repository")
    repositories = (
        Repository.objects.filter(last_used_at__lt=young)
        .filter(Q(fetched_at__isnull=True) | Q(fetched_at__lt=young))
        .exclude(pk__in=busy)
        .order_by("last_used_at")
    )
    active = Event.objects.values("actor")
    people = Person.objects.filter(last_used_at__lt=young).exclude(login__in=active)
    return repositories, people


def next_chance(now):
    """When the first repository is old enough to be deleted; in an hour if none can be found.

    Args:
        now: The time now.

    Returns:
        The time.
    """
    hours = timedelta(hours=getattr(settings, "DATABASE_MIN_AGE_HOURS", 24))
    oldest = (
        Repository.objects.order_by("last_used_at")
        .values_list("last_used_at", "fetched_at")
        .first()
    )
    if oldest is None:
        return now + timedelta(hours=1)
    return max(t for t in oldest if t is not None) + hours


def shrink(limit_mb: float | None = None) -> ShrinkReport | None:
    """Shrink the database when it is bigger than DATABASE_MAX_MB.

    When the data is bigger than DATABASE_MAX_MB: delete the data used longest ago, older than
    DATABASE_MIN_AGE_HOURS, until it is HEADROOM below the limit, so the next fetch does not
    start it again; then compact once. When only young data is left, it is not tried again
    before some of it is old enough. None without a limit, a measurable size, or before that
    time.

    Args:
        limit_mb: The limit in megabytes, ``DATABASE_MAX_MB`` if None.

    Returns:
        What was done, or None.
    """
    limit_mb = limit_mb if limit_mb is not None else getattr(settings, "DATABASE_MAX_MB", 0)
    if not limit_mb:
        return None
    now = timezone.now()
    blocked = cache.get(BLOCKED_UNTIL)
    if blocked and now < blocked:
        return None
    used = database_used()
    if used is None:
        return None
    limit = int(limit_mb * MB)
    report = ShrinkReport(before=used, after=used, limit=limit)
    if used <= limit:
        return report
    target = int(limit * (1 - HEADROOM))
    while report.after > target:
        repositories, people = removable(now)
        batch = list(repositories.values_list("pk", flat=True)[:BATCH])
        if not batch:
            report.people += people.count()
            people.delete()
            report.after = database_used() or report.after
            break
        Repository.objects.filter(pk__in=batch).delete()
        report.repositories += len(batch)
        report.after = database_used() or report.after
    if report.repositories or report.people:
        compact()
    report.enough = report.after <= limit
    if not report.enough:
        cache.set(BLOCKED_UNTIL, next_chance(now), timeout=None)
        log.warning(
            "The database uses %.1f MB, more than DATABASE_MAX_MB = %.1f MB, but the rest "
            "is younger than DATABASE_MIN_AGE_HOURS and stays.",
            report.after / MB,
            report.limit / MB,
        )
    cache.set(LAST_SHRINK, report.as_dict(), timeout=None)
    return report


def after_fetching() -> None:
    """After fetches added data, when none runs: keep the database small."""
    clean_up_daily()
    shrink()
