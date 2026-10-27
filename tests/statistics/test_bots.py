"""Bots: coveralls by default, and accounts that answer like bots as suggestions."""

from datetime import UTC, datetime, timedelta

import pytest
from django.contrib.auth import get_user_model

from community_insights import stats
from community_insights.classify import Classifier, bot_class, ensure_default_classes
from community_insights.models import ClassRule, Event, Item, Project, Repository
from community_insights.sync import store_repository

from ..fakes import repo

pytestmark = pytest.mark.django_db
T0 = datetime(2026, 1, 5, 10, tzinfo=UTC)


def answered(repository, actor, seconds: list[float], is_bot=False, author="kim"):
    """Items of the author, each answered by the actor after so many seconds."""
    start = Item.objects.filter(repository=repository).count()
    for number, delay in enumerate(seconds, start + 1):
        item = Item.objects.create(
            repository=repository,
            kind=Item.PR,
            number=number,
            author=author,
            state="open",
            created_at=T0,
            updated_at=T0,
        )
        Event.objects.create(
            item=item,
            actor=actor,
            kind=Event.COMMENT,
            at=T0 + timedelta(seconds=delay),
            is_bot=is_bot,
        )
        Event.objects.create(  # a later answer does not count, only the first one
            item=item, actor=actor, kind=Event.COMMENT, at=T0 + timedelta(days=1), is_bot=is_bot
        )


@pytest.fixture
def repository():
    """A repository for the bots."""
    return store_repository(repo("o/bots"))


def test_coveralls_is_a_bot_by_default(user):
    """Coveralls is a bot by default."""
    classify = Classifier(user)
    assert classify("coveralls", "NONE", False).name == "bot"
    assert classify("Coveralls", "NONE", False).name == "bot"
    assert classify("kim", "NONE", False).name == "external"
    assert Classifier(None)("coveralls", "", False).name == "bot", "also for visitors"


def test_accounts_that_mostly_answer_within_two_minutes(repository):
    """Accounts that mostly answer within two minutes."""
    answered(repository, "Quick-Bot", [30] * 6 + [3600] * 4)  # 6 of 10 fast
    answered(repository, "half", [30] * 5 + [3600] * 5)  # not more than half
    answered(repository, "few", [10] * 9)  # too few
    answered(repository, "app", [10] * 12, is_bot=True)  # GitHub knows it
    answered(repository, "kim", [10] * 12)  # the author answering themselves
    (suggestion,) = stats.bot_suggestions(Repository.objects.all())
    assert (suggestion.login, suggestion.items, suggestion.fast) == ("Quick-Bot", 10, 6)
    assert stats.bot_suggestions(Repository.objects.none()) == []


def test_the_classes_page_suggests_and_adds_bots(user, signed_in, repository):
    """The classes page suggests and adds bots."""
    Project.objects.create(user=user, target="o/bots").repositories.add(repository)
    answered(repository, "quick-bot", [20] * 10)
    answered(repository, "coveralls", [20] * 10)  # in the class for bots already
    page = signed_in.get("/dashboard/classes/").content.decode()
    assert "Maybe bots" in page and "quick-bot" in page
    assert 'value="coveralls"' not in page
    signed_in.post("/dashboard/classes/", {"action": "add_bot", "login": "quick-bot"})
    rule = bot_class(user).rules.get(kind=ClassRule.HANDLE)
    assert rule.value == "coveralls quick-bot"
    assert "Maybe bots" not in signed_in.get("/dashboard/classes/").content.decode()
    signed_in.post("/dashboard/classes/", {"action": "add_bot", "login": "QUICK-BOT"})
    rule.refresh_from_db()
    assert rule.value == "coveralls quick-bot", "only once"


def test_a_bot_class_without_handles_gets_a_rule(user, signed_in):
    """A bot class without handles gets a rule."""
    ensure_default_classes(user)
    bot_class(user).rules.filter(kind=ClassRule.HANDLE).delete()
    signed_in.post("/dashboard/classes/", {"action": "add_bot", "login": "renovate-me"})
    assert bot_class(user).rules.get(kind=ClassRule.HANDLE).value == "renovate-me"


@pytest.mark.parametrize("login", ["", "a b", "-x", "x" * 40, "<script>"])
def test_only_handles_are_added(user, signed_in, login):
    """Only handles are added."""
    response = signed_in.post(
        "/dashboard/classes/", {"action": "add_bot", "login": login}, follow=True
    )
    assert b"Not a GitHub handle" in response.content
    assert "coveralls" == bot_class(user).rules.get(kind=ClassRule.HANDLE).value


def test_without_a_class_for_bots(user, signed_in):
    """Without a class for bots."""
    ensure_default_classes(user)
    ClassRule.objects.filter(kind=ClassRule.BOT).delete()
    response = signed_in.post(
        "/dashboard/classes/", {"action": "add_bot", "login": "quick-bot"}, follow=True
    )
    assert b"No class for bots" in response.content


def test_the_migration_adds_coveralls_to_existing_classes(user):
    """The migration adds coveralls to existing classes."""
    from importlib import import_module

    from django.apps import apps

    ensure_default_classes(user)
    rules = bot_class(user).rules
    rules.filter(kind=ClassRule.HANDLE).delete()
    migration = import_module("community_insights.migrations.0003_coveralls_is_a_bot")
    migration.add_coveralls(apps, None)
    assert rules.get(kind=ClassRule.HANDLE).value == "coveralls"
    rules.filter(kind=ClassRule.HANDLE).update(value="renovate")
    migration.add_coveralls(apps, None)
    migration.add_coveralls(apps, None)
    assert rules.get(kind=ClassRule.HANDLE).value == "renovate coveralls"
    other = get_user_model().objects.create_user("o", "o@example.org", "pw")
    other.classes.create(name="no bots")
    migration.add_coveralls(apps, None)
    assert not ClassRule.objects.filter(person_class__user=other).exists()
