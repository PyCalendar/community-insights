"""The page Trends: issues on one side, pull requests on the other, with the time before."""

import json
import re

import pytest
from django.db.models import F

from community_insights.models import Item, Project
from community_insights.views import statistics

pytestmark = pytest.mark.django_db

WEEK = "since=2026-01-05&until=2026-01-11"  # the data of the fixture synced


@pytest.fixture
def pk(synced):
    """The number of the project of the synced repository.

    GitHub gives the time the merged pull request was closed; the fake leaves it out.
    """
    Item.objects.filter(kind=Item.PR, merged=True).update(closed_at=F("updated_at"))
    return Project.objects.get().pk


def side(page: str, kind: str) -> str:
    """The part of the page about pull requests or issues.

    Args:
        page: The HTML.
        kind: ``pr`` or ``issue``.

    Returns:
        The HTML of the section.
    """
    return re.search(rf'<section[^>]*data-kind="{kind}".*?</section>', page, re.S).group(0)


def number(section: str, name: str) -> str:
    """The number of a card of a section.

    Args:
        section: The HTML of a section.
        name: ``opened``, ``closed``, ``contributions`` or ``newcomers``.

    Returns:
        The number as shown.
    """
    found = re.search(rf'data-change="{name}">\s*<div class="number">(\d+)</div>', section)
    return found.group(1)


def test_issues_on_one_side_and_pull_requests_on_the_other(pk, signed_in):
    """Issues first, then pull requests, each with opened, closed, contributions, newcomers."""
    page = signed_in.get(f"/s/{pk}/trends/?{WEEK}").content.decode()
    assert page.index('data-kind="issue"') < page.index('data-kind="pr"')
    issues, pulls = side(page, "issue"), side(page, "pr")
    assert [number(issues, n) for n in ("opened", "closed", "contributions", "newcomers")] == [
        "1",
        "0",
        "2",
        "2",
    ], "bob opens, dave comments"
    assert [number(pulls, n) for n in ("opened", "closed", "contributions", "newcomers")] == [
        "2",
        "1",
        "4",
        "3",
    ], "bob and carol open, bob comments, maint reviews; the bot is left out"
    assert "1/1 merged" in pulls
    assert "contributions by 3 people" in pulls


def test_compared_with_the_time_before(pk, signed_in):
    """The week before had nothing: the change is the number itself, from 0."""
    page = signed_in.get(f"/s/{pk}/trends/?{WEEK}").content.decode()
    assert "the same length just before: 2025-12-29 to 2026-01-04" in page
    assert 'data-before="0"' in page and "<strong>+2</strong>" in page


def test_the_change_in_percent(pk, signed_in):
    """The second week against the first: fewer items, in percent."""
    page = signed_in.get(f"/s/{pk}/trends/?since=2026-01-07&until=2026-01-08").content.decode()
    issues = side(page, "issue")
    assert number(issues, "contributions") == "1", "dave comments on the 7th"
    pulls = side(page, "pr")
    assert "<strong>-100 %</strong>" in pulls, "carol opened on the 6th, nobody on the 7th"


def test_all_time_asks_for_a_time_range(pk, signed_in):
    """All time has no time before it to compare with."""
    page = signed_in.get(f"/s/{pk}/trends/").content.decode()
    assert "Choose a time range, such as the last 30 days" in page
    assert "data-before" not in page
    assert number(side(page, "pr"), "opened") == "2"


def test_the_new_contributors_link_to_their_pages(pk, signed_in):
    """The people who contributed for the first time, with the time range in their links."""
    page = signed_in.get(f"/s/{pk}/trends/?{WEEK}").content.decode()
    pulls = side(page, "pr")
    for login in ("bob", "carol", "maint"):
        assert f'href="/s/{pk}/people/{login}/?{WEEK.replace("&", "&amp;")}">{login}</a>' in pulls
    assert "ci[bot]" not in pulls, "bots are no new contributors"


def test_many_new_contributors_are_counted(pk, signed_in, monkeypatch):
    """Beyond the names shown, the others are counted."""
    monkeypatch.setattr(statistics, "NEWCOMERS_SHOWN", 1)
    pulls = side(signed_in.get(f"/s/{pk}/trends/?{WEEK}").content.decode(), "pr")
    assert "and 2 more" in pulls
    assert pulls.count("/people/") == 1


def test_a_time_without_new_contributors(pk, signed_in):
    """A time without contributions says so."""
    page = signed_in.get(f"/s/{pk}/trends/?since=2026-03-01&until=2026-03-07").content.decode()
    assert page.count("Nobody contributed for the first time in this time.") == 2


@pytest.mark.parametrize("name", ["trend-pr", "trend-issue", "people-pr", "people-issue"])
def test_the_charts(pk, signed_in, name):
    """Each chart as SVG and for Chart.js, linked from the page, with the time range."""
    page = signed_in.get(f"/s/{pk}/trends/?{WEEK}").content.decode()
    assert f'data-chart-src="/s/{pk}/chart/{name}.svg?{WEEK.replace("&", "&amp;")}"' in page
    svg = signed_in.get(f"/s/{pk}/chart/{name}.svg?{WEEK}")
    assert svg.status_code == 200 and svg["Content-Type"] == "image/svg+xml"
    data = json.loads(signed_in.get(f"/s/{pk}/chart/{name}.json?{WEEK}").content)
    assert data["labels"] == [f"2026-01-{d:02d}" for d in range(5, 12)]
    assert data["x"] == "day" and len(data["datasets"]) == 2 and not data["empty"]


def test_the_opened_and_closed_pull_requests_per_day(pk, signed_in):
    """The bars of the chart count by day in the time zone of the reader (Tokyo)."""
    data = json.loads(signed_in.get(f"/s/{pk}/chart/trend-pr.json?{WEEK}").content)
    opened, closed = (d["data"] for d in data["datasets"])
    assert opened == [1, 1, 0, 0, 0, 0, 0] and closed == [1, 0, 0, 0, 0, 0, 0]


def test_a_chart_without_anything_in_the_time(pk, signed_in):
    """An empty time: the SVG says so, Chart.js gets no bars to draw."""
    empty = "since=2026-03-01&until=2026-03-07"
    assert b"nothing in this time" in signed_in.get(f"/s/{pk}/chart/trend-pr.svg?{empty}").content
    assert json.loads(signed_in.get(f"/s/{pk}/chart/people-pr.json?{empty}").content)["empty"]


def test_the_charts_of_all_time_by_month(pk, signed_in):
    """All time starts with the first item and ends now: longer than half a year, by month."""
    data = json.loads(signed_in.get(f"/s/{pk}/chart/trend-issue.json").content)
    assert data["labels"][0] == "2026-01" and data["x"] == "month"


def test_the_charts_can_be_shared(pk, signed_in):
    """The page to share a chart names what it shows."""
    page = signed_in.get(f"/s/{pk}/share/people-issue/?{WEEK}").content.decode()
    assert "contributions and new contributors to issues" in page


def test_visitors_see_the_trends_of_public_repositories(synced, client):
    """A public repository has trends for everybody; projects need a sign in."""
    assert client.get("/s/o~r/trends/?last=30").status_code == 200
    assert client.get("/s/o~r/chart/trend-pr.svg?last=30").status_code == 200
    pk = Project.objects.get().pk
    assert client.get(f"/s/{pk}/trends/").status_code == 302


def test_a_wrong_time_range_is_shown_and_left_out(pk, signed_in):
    """A date that cannot be read is an error on the page, and all time is shown."""
    page = signed_in.get(f"/s/{pk}/trends/?since=yesterday").content.decode()
    assert "is no date like 2026-01-31" in page
    assert "Choose a time range" in page


@pytest.mark.parametrize("days", [7, 30, 90])
def test_the_last_days_are_quick_choices(pk, signed_in, days):
    """Each page offers the last 7, 30 and 90 days; the one shown is marked."""
    page = signed_in.get(f"/s/{pk}/trends/?last={days}").content.decode()
    assert f'aria-current="true" href="/s/{pk}/trends/?last={days}" data-last-days="{days}"' in page
    assert page.count('aria-current="true"') == 1
    assert "the same length just before" in page


def test_the_quick_choices_keep_the_parameters_of_the_page(pk, signed_in):
    """The query of the page Contributors stays, the dates go; the classes of a link stay."""
    page = signed_in.get(
        f"/s/{pk}/contributors/?where=prs_total>0&since=2026-01-01"
    ).content.decode()
    assert f'href="/s/{pk}/contributors/?last=7&amp;where=prs_total%3E0" data-last-days="7"' in page
    assert 'aria-current="true"' not in page, "a date is no quick choice"


def test_the_page_in_german(pk, signed_in):
    """The texts of the page are translated."""
    page = signed_in.get(f"/s/{pk}/trends/?{WEEK}", HTTP_ACCEPT_LANGUAGE="de").content.decode()
    assert "Neue Beitragende" in page and "Letzte 30 Tage" in page
    assert "Beiträge von 3 Personen" in page
