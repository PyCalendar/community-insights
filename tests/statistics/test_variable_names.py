"""The variables have the names of the command line tool before; saved queries follow."""

from importlib import import_module

import pytest
from django.apps import apps

from community_insights import query
from community_insights.errors import UnknownVariable
from community_insights.models import SavedQuery

PREFIXES = ("user_", "commits_", "prs_", "issues_", "comments_", "actions_", "activity_")
UNITS = ("hours_", "days_", "months_")


@pytest.mark.parametrize("name", list(query.VARIABLES))
def test_every_variable_has_a_prefix(name):
    """Every variable has a prefix."""
    assert name.startswith(PREFIXES + UNITS), name


def test_the_names_of_the_tool_before_are_there():
    """The names of the tool before are there."""
    for name in (
        "user_handle",
        "user_association",
        "user_bot",
        "commits_total",
        "prs_total",
        "prs_open",
        "prs_merged",
        "prs_unmerged",
        "prs_closed",
        "prs_commented",
        "prs_reviewed",
        "issues_opened",
        "issues_open",
        "issues_closed",
        "issues_commented",
        "comments_total",
        "actions_merges",
        "days_first",
        "days_last",
        "days_to_merge",
        "months_active",
    ):
        assert name in query.VARIABLES, name


def test_old_names_say_what_they_are_called_now():
    """Old names say what they are called now."""
    with pytest.raises(UnknownVariable, match="It is called prs_total now"):
        query.parse("prs_opened > 1")
    with pytest.raises(UnknownVariable, match="Did you mean prs_merged"):
        query.parse("prs_merge > 1")


@pytest.mark.django_db
def test_saved_queries_get_the_new_names(user):
    """Saved queries get the new names."""
    saved = SavedQuery.objects.create(
        user=user,
        name="old",
        where='prs_opened > 2 and not bot and "class" in location and prs_closed < 1',
        sort="-response_hours",
        columns="login class comments",
        group="country",
        chart="activity",
    )
    import_module("community_insights.migrations.0005_saved_query_names_as_before").forwards(
        apps, None
    )
    saved.refresh_from_db()
    assert saved.where == (
        'prs_total > 2 and not user_bot and "class" in user_location and prs_unmerged < 1'
    ), "text in quotes stays; prs_closed meant without merging"
    assert saved.sort == "-hours_to_respond"
    assert saved.columns == "user_handle user_class comments_total"
    assert (saved.group, saved.chart) == ("user_country", "activity_total")
    query.parse(saved.where)
