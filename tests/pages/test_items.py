"""The list of pull requests and issues."""

import re
from datetime import timedelta

import pytest
from django.contrib.auth.models import AnonymousUser

from community_insights.classify import Classifier, add_handle, bot_class
from community_insights.models import ClassRule, Item, Repository
from community_insights.tables.items import bot_logins, items_with_responses

pytestmark = pytest.mark.django_db


def rows(response) -> str:
    """The page as text."""
    return response.content.decode()


def test_items_filtered_and_sorted(world, signed_in):  # noqa: F811
    """Items filtered and sorted."""
    pk = world["project"].pk
    page = rows(signed_in.get(f"/s/{pk}/items/"))
    assert "o/r#1" in page and "o/r#3" in page
    issues = rows(signed_in.get(f"/s/{pk}/items/?kind=issue"))
    assert "/issues/1" in issues and "/pull/1" not in issues
    merged = rows(signed_in.get(f"/s/{pk}/items/?state=merged"))
    assert "/pull/1" in merged and "/pull/2" not in merged
    silent = rows(signed_in.get(f"/s/{pk}/items/?responded=false"))
    assert "waiting" in silent and "/pull/1<" not in silent.replace('"', "<")
    answered = rows(signed_in.get(f"/s/{pk}/items/?responded=true"))
    assert "/pull/1" in answered and "waiting" not in answered
    by_response = rows(signed_in.get(f"/s/{pk}/items/?sort=response"))
    assert by_response.index("/pull/1") < by_response.index("/issues/1"), "10 minutes before 2 days"
    assert signed_in.get(f"/s/{pk}/items/?state=nonsense").status_code == 200


def row(page: str, link: str) -> str:
    """The text of the row of the table with a link, without its tags."""
    start = page.index(f'{link}"')
    return re.sub(r"<[^>]+>", " ", page[start : page.index("</tr>", start)])


def test_a_bot_is_no_first_response(world, signed_in):  # noqa: F811
    """ci[bot] comments after 10 minutes, the review of maint comes after 2 hours: 2 hours."""
    page = rows(signed_in.get(f"/s/{world['project'].pk}/items/"))
    assert "2h" in row(page, "/pull/1")
    assert "10min" not in row(page, "/pull/1")


def test_a_handle_of_the_bot_class_is_no_first_response(world, signed_in, user):  # noqa: F811
    """An account that the bot class names by its handle does not respond either."""
    add_handle(bot_class(user), "maint")
    page = rows(signed_in.get(f"/s/{world['project'].pk}/items/"))
    assert "waiting" in row(page, "/pull/1"), "bob is the author, ci[bot] and maint are bots"


def test_without_the_rule_is_a_bot_bots_respond(world, signed_in, user):  # noqa: F811
    """Classes without the rule "is a bot" count the bots as everyone else."""
    ClassRule.objects.filter(person_class__user=user, kind=ClassRule.BOT).delete()
    page = rows(signed_in.get(f"/s/{world['project'].pk}/items/"))
    assert "10min" in row(page, "/pull/1")


def test_without_classes_everyone_responds(world):  # noqa: F811
    """Without a classifier, the first comment of somebody else counts, also of a bot."""
    found = items_with_responses(Repository.objects.filter(full_name="o/r"))
    first = found.get(kind=Item.PR, number=1)
    assert first.response == timedelta(minutes=10)


def test_the_bots_of_visitors_are_those_of_the_default_classes(world):  # noqa: F811
    """A visitor gets the default classes: GitHub bots and coveralls are bots."""
    repositories = Repository.objects.filter(full_name="o/r")
    bots = bot_logins(repositories, Classifier(AnonymousUser()))
    assert bots == {"ci[bot]"}
    found = items_with_responses(repositories, classifier=Classifier(AnonymousUser()))
    assert found.get(kind=Item.PR, number=1).response == timedelta(hours=2)
