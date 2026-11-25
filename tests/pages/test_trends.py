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
    names = ("opened", "merged", "closed", "contributions", "newcomers")
    assert [number(pulls, n) for n in names] == [
        "2",
        "1",
        "0",
        "4",
        "3",
    ], "bob and carol open, bob comments, maint reviews; the bot is left out"
    assert "closed without merging" in pulls and 'data-change="merged"' not in issues
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
        assert f'href="/s/o~r/people/{login}/?{WEEK.replace("&", "&amp;")}">{login}</a>' in pulls
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
    assert f'data-chart-src="/s/o~r/chart/{name}.svg?{WEEK.replace("&", "&amp;")}"' in page
    svg = signed_in.get(f"/s/{pk}/chart/{name}.svg?{WEEK}")
    assert svg.status_code == 200 and svg["Content-Type"] == "image/svg+xml"
    data = json.loads(signed_in.get(f"/s/{pk}/chart/{name}.json?{WEEK}").content)
    assert data["labels"] == [f"2026-01-{d:02d}" for d in range(5, 12)]
    bars = 3 if name == "trend-pr" else 2  # opened, closed without merging, merged
    assert data["x"] == "day" and len(data["datasets"]) == bars and not data["empty"]


def test_the_opened_and_closed_pull_requests_per_day(pk, signed_in):
    """The bars of the chart count by day in the time zone of the reader (Tokyo)."""
    data = json.loads(signed_in.get(f"/s/{pk}/chart/trend-pr.json?{WEEK}").content)
    assert [d["label"] for d in data["datasets"]] == ["opened", "closed without merging", "merged"]
    opened, closed, merged = (d["data"] for d in data["datasets"])
    assert opened == [1, 1, 0, 0, 0, 0, 0] and merged == [1, 0, 0, 0, 0, 0, 0]
    assert closed == [0] * 7, "the only closed one was merged"


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
    """A public repository has trends for everybody; its project leads there."""
    assert client.get("/s/o~r/trends/?last=30").status_code == 200
    assert client.get("/s/o~r/chart/trend-pr.svg?last=30").status_code == 200
    pk = Project.objects.get().pk
    assert client.get(f"/s/{pk}/trends/").request["PATH_INFO"] == "/s/o~r/trends/"


def test_a_wrong_time_range_is_shown_and_left_out(pk, signed_in):
    """A date that cannot be read is an error on the page, and all time is shown."""
    page = signed_in.get(f"/s/{pk}/trends/?since=yesterday").content.decode()
    assert "is no date like 2026-01-31" in page
    assert "Choose a time range" in page


@pytest.mark.parametrize("days", [7, 30, 90])
def test_the_last_days_are_quick_choices(pk, signed_in, days):
    """Each page offers the last 7, 30 and 90 days; the one shown is marked."""
    page = signed_in.get(f"/s/{pk}/trends/?last={days}").content.decode()
    assert f'aria-current="true" href="/s/o~r/trends/?last={days}" data-last-days="{days}"' in page
    assert page.count('aria-current="true"') == 1
    assert "the same length just before" in page


def test_the_quick_choices_keep_the_parameters_of_the_page(pk, signed_in):
    """The query of the page Contributors stays, the dates go; the classes of a link stay."""
    page = signed_in.get(
        f"/s/{pk}/contributors/?where=prs_total>0&since=2026-01-01"
    ).content.decode()
    assert 'href="/s/o~r/contributors/?last=7&amp;where=prs_total%3E0" data-last-days="7"' in page
    assert 'aria-current="true"' not in page, "a date is no quick choice"


def test_the_page_in_german(pk, signed_in):
    """The texts of the page are translated."""
    page = signed_in.get(f"/s/{pk}/trends/?{WEEK}", HTTP_ACCEPT_LANGUAGE="de").content.decode()
    assert "Neue Beitragende" in page and "Letzte 30 Tage" in page
    assert "Beiträge von 3 Personen" in page


def test_what_a_contribution_is(pk, signed_in):
    """The page says what counts: openings, comments, reviews by people; commits do not."""
    page = signed_in.get(f"/s/{pk}/trends/?{WEEK}").content.decode()
    text = re.search(r"<p[^>]*data-contributions>.*?</p>", page, re.S).group(0)
    assert "a comment or a review" in text and "bots are left out" in text
    assert "Commits, reactions, labels and closing are no contributions" in text
    assert "explanation/trends.html#contributions" in text


def test_too_little_data_for_a_statistical_trend(pk, signed_in):
    """A week of the fixture has too few contributions for a trend."""
    pulls = side(signed_in.get(f"/s/{pk}/trends/?{WEEK}").content.decode(), "pr")
    assert "Contributions: too little data for a trend." in pulls
    assert "Contributors: too little data for a trend." in pulls
    assert "data-p-value" not in pulls


@pytest.fixture
def busy(pk):
    """More and more comments on the issue each day of a week (3, 6, ... 21), by more people."""
    from community_insights.models import Event

    issue = Item.objects.get(kind=Item.ISSUE)
    for number in range(1, 8):
        for person in range(number * 3):
            Event.objects.create(
                item=issue,
                actor=f"p{person}",
                kind=Event.COMMENT,
                at=f"2026-02-{number + 1:02d}T03:00:00Z",
            )
    return pk


def test_a_statistically_significant_growth(busy, signed_in):
    """First whether it is significant, then how much, the error margin, interval, p-value."""
    page = signed_in.get(f"/s/{busy}/trends/?since=2026-02-02&until=2026-02-08").content.decode()
    issues = side(page, "issue")
    model = re.search(r'<li[^>]*data-count-trend="contributions".*?</li>', issues, re.S).group(0)
    assert 'data-significant="yes"' in model
    verdict = re.search(r"<span data-verdict>(.*?)</span>", model, re.S).group(1)
    assert re.search(r"Contributions: a significant increase of \d+ % per day\.", verdict)
    assert model.index("data-verdict") < model.index("Error margin"), "the verdict comes first"
    assert re.search(r"Error margin ±\d+ percentage points: with 95 % confidence", model)
    assert re.search(r"between \+\d+ % and \+\d+ % per day \(p = 0\.0\d+;", model)
    assert "The fitted line goes from" in model
    people = re.search(r'<li[^>]*data-count-trend="contributors".*?</li>', issues, re.S).group(0)
    assert "Contributors: a significant increase of" in people


def test_a_trend_that_is_not_significant(pk, signed_in):
    """The same few comments each day: no clear trend, said in words."""
    from community_insights.models import Event

    issue = Item.objects.get(kind=Item.ISSUE)
    for number, count in enumerate([3, 2, 3, 2, 3, 2, 3], start=2):
        for person in range(count):
            Event.objects.create(
                item=issue,
                actor=f"p{person}",
                kind=Event.COMMENT,
                at=f"2026-02-{number:02d}T03:00:00Z",
            )
    page = signed_in.get(f"/s/{pk}/trends/?since=2026-02-02&until=2026-02-08").content.decode()
    issues = side(page, "issue")
    assert "<strong>Contributions: no significant trend.</strong>" in issues
    assert re.search(r"The change of [+-]?\d+ % per day may be chance\.", issues)


@pytest.mark.parametrize(
    ("query", "x", "first"),
    [
        ("since=2026-01-05&until=2026-01-11", "day", "2026-01-05"),
        ("since=2026-01-01&until=2026-03-01", "calendar week (ISO 8601, from Monday)", "CW 1 2026"),
        ("since=2026-01-01&until=2026-12-31", "month", "2026-01"),
        ("since=2022-01-01&until=2026-12-31", "year", "2022"),
    ],
)
def test_the_bars_follow_the_time_range(pk, signed_in, query, x, first):
    """A week by day, two months by calendar week, a year by month, five years by year."""
    data = json.loads(signed_in.get(f"/s/{pk}/chart/trend-pr.json?{query}").content)
    assert data["labels"][0] == first and len(data["labels"]) <= 31
    assert data["x"] == x


def test_the_reader_chooses_the_bars(pk, signed_in):
    """?by=month: the charts of the page keep it; the choice is on the page."""
    page = signed_in.get(f"/s/{pk}/trends/?{WEEK}&by=month").content.decode()
    assert f"/chart/trend-pr.svg?{WEEK.replace('&', '&amp;')}&amp;by=month" in page
    assert '<option value="month" selected>months</option>' in page
    assert 'name="by" data-submit-on-change' in page
    data = json.loads(signed_in.get(f"/s/{pk}/chart/trend-pr.json?{WEEK}&by=month").content)
    assert data["labels"] == ["2026-01"]


def test_an_unknown_choice_of_bars_is_automatic(pk, signed_in):
    """?by=decade is ignored."""
    page = signed_in.get(f"/s/{pk}/trends/?{WEEK}&by=decade").content.decode()
    assert '<option value="" selected>automatic</option>' in page
    assert "by=decade" not in page.split("data-chart-src")[1], "not in the charts"


def test_charts_keep_their_space_while_they_load(pk, signed_in):
    """Each chart has the width and height of its SVG, in a frame for the spinner."""
    page = signed_in.get(f"/s/{pk}/trends/?{WEEK}").content.decode()
    assert page.count("data-chart-frame") == 4
    assert 'width="504" height="202" loading="lazy"' in page
    svg = signed_in.get(f"/s/{pk}/chart/trend-pr.svg?{WEEK}").content.decode()
    assert 'width="504pt" height="201.6pt"' in svg, "the SVG has exactly that size"
    empty = signed_in.get(f"/s/{pk}/chart/trend-pr.svg?since=2026-03-01&until=2026-03-07")
    assert b'width="504pt" height="201.6pt"' in empty.content, "also without data"
