"""The estimate of a fetch and how complete the data is."""

from datetime import timedelta

import pytest
from django.utils import timezone

from community_insights import pipeline
from community_insights.models import Item
from community_insights.sync import store_repository
from tests.factories import FetchJobFactory

from ..fakes import FakeClient, item, repo, run

pytestmark = pytest.mark.django_db


def test_estimate_first_fetch_and_later(user):  # noqa: F811
    """Estimate first fetch and later."""
    repository = store_repository(repo("o/r"))
    client = FakeClient(prs=[item(i, "a", "2026-01-01T00:00:00Z", reviews=[]) for i in range(120)])
    (estimate,) = run(pipeline.estimate, [repository], client)
    assert (estimate.prs, estimate.issues, estimate.cached) == (120, 0, 0)
    assert estimate.points >= 3  # three pages at least
    repository.refresh_from_db()
    assert repository.prs_total == 120
    repository.prs_synced_until = timezone.now()
    assert pipeline.points_for(repository, 120, 0, 120) == 3  # read before: only changes


def test_estimate_of_a_repository_the_token_cannot_see(user):  # noqa: F811
    """Estimate of a repository the token cannot see."""
    repository = store_repository(repo("o/secret"))
    (estimate,) = run(pipeline.estimate, [repository], FakeClient(hidden={"o/secret"}))
    assert estimate.prs is None and estimate.points == 0


def test_completeness_without_and_with_data(user):  # noqa: F811
    """Completeness without and with data."""
    repository = store_repository(repo("o/r"))
    data = pipeline.completeness([repository])
    assert data["percent"] == 0 and data["total"] is None and data["seconds_left"] is None
    repository.prs_total, repository.issues_total = 4, 0
    repository.save()
    Item.objects.create(
        repository=repository,
        kind="pr",
        number=1,
        state="open",
        created_at=timezone.now(),
        updated_at=timezone.now(),
    )
    data = pipeline.completeness([repository])
    assert (data["percent"], data["items"], data["total"]) == (25, 1, 4)
    assert pipeline.completeness([])["percent"] == 100


def test_empty_repository_is_complete(user):  # noqa: F811
    """Empty repository is complete."""
    repository = store_repository(repo("o/empty"))
    repository.prs_total = repository.issues_total = 0
    repository.save()
    assert pipeline.completeness([repository])["percent"] == 100


def test_seconds_left(user):  # noqa: F811
    """Seconds left."""
    job = FetchJobFactory(user=user, repository__full_name="o/r", items_expected=200, items_done=0)
    assert pipeline.seconds_left([job]) == pytest.approx(200 / pipeline.ITEMS_PER_SECOND)
    waiting = FetchJobFactory(
        user=user,
        repository__full_name="o/w",
        items_expected=0,
        not_before=timezone.now() + timedelta(seconds=60),
    )
    assert pipeline.seconds_left([waiting]) == pytest.approx(60, abs=2)
