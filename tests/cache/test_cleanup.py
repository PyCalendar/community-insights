"""Deleting what nobody used, by hand and once a day."""

from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from community_insights.models import Item, Project, Repository

pytestmark = pytest.mark.django_db


def test_viewing_marks_the_repository_used(synced, signed_in):
    Repository.objects.update(last_used_at=timezone.now() - timedelta(days=100))
    signed_in.get(f"/s/{Project.objects.get().pk}/")
    assert Repository.objects.get().last_used_at > timezone.now() - timedelta(minutes=1)


def test_clear_cache_command_and_page(synced, signed_in):
    Repository.objects.update(last_used_at=timezone.now() - timedelta(days=40))
    call_command("clear_cache", "--days", "30", "--dry-run")
    assert Repository.objects.count() == 1
    call_command("clear_cache", "--days", "30")
    assert Repository.objects.count() == 0 and Item.objects.count() == 0
    assert Project.objects.count() == 1  # the project stays; it is read again


def test_cache_page_deletes_one_repository(synced, signed_in):
    signed_in.post("/dashboard/cache/", {"repository": Repository.objects.get().pk})
    assert Repository.objects.count() == 0


def test_unused_data_is_cleaned_up_once_a_day(world, settings):  # noqa: F811
    from datetime import timedelta

    from django.core.cache import cache

    from community_insights.cleanup import LAST_CLEANUP, clean_up_daily

    cache.delete(LAST_CLEANUP)
    Repository.objects.filter(full_name="o/empty").update(
        last_used_at=timezone.now() - timedelta(days=100)
    )
    assert clean_up_daily() == (1, 0)
    assert not Repository.objects.filter(full_name="o/empty").exists()
    assert Project.objects.filter(target="o/empty").exists(), "the project stays"
    assert clean_up_daily() is None, "not again on the same day"
    cache.delete(LAST_CLEANUP)
    settings.CACHE_KEEP_DAYS = 0
    assert clean_up_daily() is None, "0 keeps everything"
