"""Keeping the database below DATABASE_MAX_MB."""

import logging
from datetime import timedelta

import pytest
from django.utils import timezone

from community_insights import cleanup
from community_insights.models import FetchJob, Item, Repository
from community_insights.sync import read_repository, store_repository

from ..fakes import FakeClient, item, repo

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture(autouse=True)
def _fresh():
    """No wait of an earlier test is left in the cache."""
    from django.core.cache import cache

    cache.delete(cleanup.BLOCKED_UNTIL)
    yield
    cache.delete(cleanup.BLOCKED_UNTIL)


def fill(name: str, days_ago: float, items: int = 40) -> Repository:
    repository = store_repository(repo(name))
    body = [item(i, "a", "2026-01-01T00:00:00Z", reviews=[]) for i in range(1, items + 1)]
    for data in body:
        data["title"] = "x" * 400  # some size
    read_repository(FakeClient(prs=body), repository)
    old = timezone.now() - timedelta(days=days_ago)
    Repository.objects.filter(pk=repository.pk).update(last_used_at=old, fetched_at=old)
    return repository


def test_no_limit_no_shrinking(settings):
    settings.DATABASE_MAX_MB = 0
    assert cleanup.shrink() is None


def test_the_data_used_longest_ago_goes_first_and_young_data_stays(settings, caplog):
    settings.DATABASE_MIN_AGE_HOURS = 24
    fill("o/oldest", days_ago=30)
    fill("o/old", days_ago=10)
    fill("o/young", days_ago=0.1)
    size = cleanup.database_size()
    assert size
    # a limit that cannot be reached without the young data
    with caplog.at_level(logging.WARNING, logger="community_insights.cleanup"):
        report = cleanup.shrink(limit_mb=0.001)
    assert report.repositories == 2 and not report.enough
    assert list(Repository.objects.values_list("full_name", flat=True)) == ["o/young"]
    assert Item.objects.filter(repository__full_name="o/young").count() == 40
    assert "younger than DATABASE_MIN_AGE_HOURS" in caplog.text


def test_a_limit_that_fits_deletes_nothing(settings):
    fill("o/old", days_ago=30)
    report = cleanup.shrink(limit_mb=10_000)
    assert report.enough and report.repositories == 0
    assert Repository.objects.count() == 1


def test_repositories_being_fetched_stay(user):  # noqa: F811
    repository = fill("o/old", days_ago=30)
    FetchJob.objects.create(user=user, repository=repository, status=FetchJob.QUEUED)
    report = cleanup.shrink(limit_mb=0.001)
    assert Repository.objects.filter(pk=repository.pk).exists() and not report.enough


def test_the_check_runs_after_fetching(user, settings, monkeypatch):  # noqa: F811
    from community_insights import pipeline
    from community_insights.models import AccessToken

    calls = []
    monkeypatch.setattr(
        "community_insights.pipeline.worker.after_fetching", lambda: calls.append(1)
    )
    AccessToken.objects.create(user=user, token="t", login="x")
    FetchJob.objects.create(user=user, repository=store_repository(repo("o/r")))
    pipeline.work(once=True, make_client=lambda token: FakeClient())
    assert calls == [1]


def test_the_cache_page_shows_the_size(user, client, settings):  # noqa: F811
    settings.DATABASE_MAX_MB = 50
    client.force_login(user)
    page = client.get("/dashboard/cache/").content.decode()
    assert "Kept below 50" in page and "MB" in page


def test_no_work_when_only_young_data_is_left(settings, monkeypatch):
    """Adding data again and again does not compact again and again."""
    compacted = []
    monkeypatch.setattr(cleanup, "compact", lambda: compacted.append(1))
    fill("o/young", days_ago=0.1)
    first = cleanup.shrink(limit_mb=0.001)
    assert not first.enough and compacted == [], "nothing deleted: nothing to compact"
    for _ in range(5):
        assert cleanup.shrink(limit_mb=0.001) is None, "waits until data is old enough"
    assert compacted == []


def test_shrinking_leaves_room_below_the_limit(settings):
    empty = cleanup.database_used()  # the tables of Django, users, ...
    for i in range(6):
        fill(f"o/r{i}", days_ago=30 - i, items=60)
    used = cleanup.database_used()
    limit_mb = (empty + (used - empty) * 0.6) / cleanup.MB
    report = cleanup.shrink(limit_mb=limit_mb)
    assert report.enough
    assert report.after <= report.limit * (1 - cleanup.HEADROOM)
    names = set(Repository.objects.values_list("full_name", flat=True))
    assert "o/r0" not in names and "o/r5" in names, "the one used longest ago went first"
    assert cleanup.shrink(limit_mb=limit_mb).repositories == 0, "room for the next fetches"


def test_compact_once_however_many_batches(settings, monkeypatch):
    calls = []
    real = cleanup.compact
    monkeypatch.setattr(cleanup, "compact", lambda: (calls.append(1), real()))
    for i in range(12):
        fill(f"o/r{i}", days_ago=30, items=10)
    report = cleanup.shrink(limit_mb=0.001)
    assert report.repositories == 12 and calls == [1]
