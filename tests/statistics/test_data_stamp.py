"""The stamp of the data and the results kept with it (data_stamp.py)."""

import pytest
from cachalot import api
from django.core.cache import cache
from django.utils import timezone

from community_insights import data_stamp
from community_insights.models import Person, Repository
from community_insights.models.cached import TOUCH_EVERY

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _empty_cache():
    """Each test starts with an empty cache."""
    cache.clear()


def test_the_tables_of_the_data():
    """The stamp watches the tables of the site, also those of many-to-many fields."""
    tables = data_stamp.tables()
    for table in ("community_item", "community_event", "community_project_repositories"):
        assert table in tables
    assert "django_session" not in tables, "signing in does not change the data"


def test_the_stamp_stays_while_nothing_changes():
    """Reading gives the same stamp."""
    assert data_stamp.stamp(now=0) == data_stamp.stamp(now=0)
    Person.objects.count()
    assert data_stamp.stamp(now=0) == data_stamp.stamp(now=0)


def test_a_write_gives_a_new_stamp():
    """A write of a table gives a new stamp."""
    before = data_stamp.stamp(now=0)
    Person.objects.create(login="bob")
    assert data_stamp.stamp(now=0) != before


def test_the_hour_is_in_the_stamp():
    """Another hour, another stamp; the same hour, the same."""
    assert data_stamp.stamp(now=0) == data_stamp.stamp(now=data_stamp.HOUR - 1)
    assert data_stamp.stamp(now=0) != data_stamp.stamp(now=data_stamp.HOUR)


def test_a_forgotten_note_never_gives_an_older_stamp():
    """A cleared cache does not bring back the stamp of older data: the note is made now."""
    first = data_stamp.changed("community_person")
    cache.clear()
    again = data_stamp.changed("community_person")
    assert again >= first > 0
    assert data_stamp.changed("community_person") == again, "and then it stays"


def test_the_version_is_in_the_stamp(monkeypatch):
    """A new version of the site draws differently: another stamp."""
    before = data_stamp.stamp(now=0)
    monkeypatch.setattr(data_stamp.version, "get", lambda: {"version": "9.9.9"})
    assert data_stamp.stamp(now=0) != before


def test_kept_computes_once_per_stamp():
    """kept computes once, until the data changes."""
    computed = []

    def compute():
        """Count the computations."""
        computed.append(1)
        return [len(computed)]

    assert data_stamp.kept("test", ["a"], compute) == [1]
    assert data_stamp.kept("test", ["a"], compute) == [1]
    assert data_stamp.kept("test", ["b"], compute) == [2], "other parts, another result"
    api.invalidate("community_item")
    assert data_stamp.kept("test", ["a"], compute) == [3], "the data changed"


def test_kept_computes_each_time_without_cachalot(settings):
    """Without cachalot nothing notes the changes: computed each time."""
    settings.CACHALOT_ENABLED = False
    computed = []
    data_stamp.kept("test", [], lambda: computed.append(1))
    data_stamp.kept("test", [], lambda: computed.append(1))
    assert len(computed) == 2


def test_touch_writes_only_after_an_hour():
    """Using a repository writes the table at most once an hour."""
    repository = Repository.objects.create(full_name="o/r", owner_login="o")
    assert Repository.touch_all(Repository.objects.all()) == 0, "just created"
    before = data_stamp.changed("community_repository")
    Repository.touch_all(Repository.objects.all())
    assert data_stamp.changed("community_repository") == before, "no write"
    old = timezone.now() - TOUCH_EVERY - timezone.timedelta(minutes=1)
    Repository.objects.filter(pk=repository.pk).update(last_used_at=old)
    assert Repository.touch_all(Repository.objects.all()) == 1
    repository.refresh_from_db()
    assert repository.last_used_at > old


def test_touch_of_one_object():
    """touch of one object writes it after an hour."""
    person = Person.objects.create(login="bob")
    Person.objects.filter(pk=person.pk).update(last_used_at=timezone.now() - 2 * TOUCH_EVERY)
    person.touch()
    person.refresh_from_db()
    assert timezone.now() - person.last_used_at < TOUCH_EVERY
