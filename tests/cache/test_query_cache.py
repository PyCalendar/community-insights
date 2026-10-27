"""The statistics cached by django-cachalot change with the data."""

import pytest

from community_insights import stats
from community_insights.models import Item, Repository

from ..fakes import item
from ..fakes.client import FakeClient

pytestmark = pytest.mark.django_db


def test_cached_statistics_change_with_the_data(world):  # noqa: F811
    """django-cachalot keeps answers until the tables change."""
    repositories = Repository.objects.all()
    before = stats.counts(repositories)["prs"]["total"]
    assert stats.counts(repositories)["prs"]["total"] == before  # from the cache
    from community_insights.sync import read_repository

    more = FakeClient(prs=[item(9, "zed", "2026-03-01T00:00:00Z", reviews=[])])
    read_repository(more, world["repository"])
    assert stats.counts(repositories)["prs"]["total"] == before + 1
    assert Item.objects.filter(number=9).exists()
