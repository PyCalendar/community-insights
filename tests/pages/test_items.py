"""The list of pull requests and issues."""

import re
from datetime import timedelta

import pytest
from django.contrib.auth.models import AnonymousUser

from community_insights.classify import Classifier, add_handle, bot_class
from community_insights.models import ClassRule, Item, Repository
from community_insights.stats import items_in
from community_insights.tables.items import items_with_responses

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
    assert "/pull/1" in answered and "waiting" not in row(answered, "/pull/1")
    assert "waiting" in row(answered, "/issues/1"), "dave answered, but he is no collaborator"
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
    found = row(page, "/pull/1")
    assert "no response" in found, "bob is the author, ci[bot] and maint are bots"
    assert "waiting" not in found, "it is merged: it waits no more"


def test_without_the_rule_is_a_bot_bots_respond(world, signed_in, user):  # noqa: F811
    """Classes without the rule "is a bot" count the bots as everyone else."""
    ClassRule.objects.filter(person_class__user=user, kind=ClassRule.BOT).delete()
    page = rows(signed_in.get(f"/s/{world['project'].pk}/items/"))
    assert "10min" in row(page, "/pull/1")


def pull_request_1(classifier=None):
    """Pull request 1 of o/r with its first response.

    Args:
        classifier: Decides who is a bot; None for those GitHub marks.

    Returns:
        The item.
    """
    found = items_with_responses(items_in(Repository.objects.filter(full_name="o/r")), classifier)
    return next(i for i in found if i.kind == Item.PR and i.number == 1)


def test_without_classes_the_bots_of_github_do_not_respond(world):  # noqa: F811
    """Without a classifier, GitHub's mark decides: ci[bot] is no response, maint is."""
    assert pull_request_1().response == timedelta(hours=2)


def test_the_bots_of_visitors_are_those_of_the_default_classes(world):  # noqa: F811
    """A visitor gets the default classes: GitHub bots and coveralls are bots."""
    assert pull_request_1(Classifier(AnonymousUser())).response == timedelta(hours=2)


def test_the_filters_are_multiple_choices_all_chosen_by_default(world, signed_in):  # noqa: F811
    """Closed and merged together; responded yes and no; without a choice all are chosen."""
    pk = world["project"].pk
    page = rows(signed_in.get(f"/s/{pk}/items/"))
    for name, value in (("state", "open"), ("state", "merged"), ("responded", "false")):
        assert re.search(rf'name="{name}"\s+value="{value}"[^>]*checked', page), (name, value)
    closed_and_merged = rows(signed_in.get(f"/s/{pk}/items/?state=closed&state=merged"))
    assert "/pull/1" in closed_and_merged and "/pull/3" in closed_and_merged
    assert "/pull/2" not in closed_and_merged, "PR 2 is open"
    only_closed = rows(signed_in.get(f"/s/{pk}/items/?state=closed"))
    assert "/pull/3" in only_closed and "/pull/1<" not in only_closed.replace('"', "<")
    both = rows(signed_in.get(f"/s/{pk}/items/?responded=true&responded=false"))
    assert "/pull/1" in both and "/pull/2" in both


def test_the_state_is_the_second_column_in_the_colours_of_github(world, signed_in):  # noqa: F811
    """Open green, closed red, merged purple, right after the item."""
    page = rows(signed_in.get(f"/s/{world['project'].pk}/items/"))
    start = page.rindex("<thead", 0, page.index(">Item<"))
    head = page[start : page.index("</thead>", start)]
    titles = [t for t in (re.sub(r"<[^>]+>", " ", head).split()) if t]
    assert titles[:2] == ["Item", "State"]
    assert '<span class="badge state-merged">merged</span>' in page
    assert '<span class="badge state-open">open</span>' in page
    assert '<span class="badge state-closed">closed</span>' in page
