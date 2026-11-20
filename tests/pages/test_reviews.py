"""The page Reviews: numbers, the statistical trend first, kinds, and reviews until merged."""

import json
import re

import pytest

from community_insights.models import Project

from ..statistics.test_reviews import reviewed  # noqa: F401

pytestmark = pytest.mark.django_db

WEEK = "since=2026-01-08&until=2026-01-14"


@pytest.fixture
def pk(reviewed, user):  # noqa: F811
    """A project of the user with the reviewed repository.

    Returns:
        Its number.
    """
    project = Project.objects.create(user=user, target="o/r")
    project.repositories.add(*reviewed)
    return project.pk


def test_the_numbers_of_the_page(pk, signed_in):
    """All reviews, by collaborators, by others, and the median until merged."""
    page = signed_in.get(f"/s/{pk}/reviews/?{WEEK}").content.decode()
    for name, number in (("total", 4), ("collaborators", 2), ("others", 2)):
        assert re.search(rf'data-change="{name}">\s*<div class="number">{number}</div>', page)
    assert "reviews by 3 people" in page
    assert "Collaborators</strong> are the owners, members and collaborators" in page
    assert "2 pull requests were merged in this time." in page
    assert "1 were merged without a review" in page


def test_the_kinds_of_review_in_a_table(pk, signed_in):
    """Each kind with the reviews by collaborators and by others."""
    page = signed_in.get(f"/s/{pk}/reviews/?{WEEK}").content.decode()
    row = re.search(r'<tr data-kind="changes_requested">.*?</tr>', page, re.S).group(0)
    assert "changes requested" in row and re.findall(r">(\d+)</td>", row) == ["0", "1"]


def test_the_trend_says_first_whether_it_is_significant(pk, signed_in):
    """A week of a few reviews: too little data, or no significant trend, said first."""
    page = signed_in.get(f"/s/{pk}/reviews/?{WEEK}").content.decode()
    models = re.findall(r'<li[^>]*data-count-trend="(\w+)"', page)
    assert models == ["total", "collaborators", "others"]
    assert "Reviews: too little data for a trend." in page


@pytest.mark.parametrize("name", ["reviews-time", "reviews-kinds", "reviews-merge"])
def test_the_charts(pk, signed_in, name):
    """Each chart as SVG and for Chart.js, linked from the page."""
    page = signed_in.get(f"/s/{pk}/reviews/?{WEEK}").content.decode()
    assert f"/chart/{name}.svg?" in page
    svg = signed_in.get(f"/s/{pk}/chart/{name}.svg?{WEEK}")
    assert svg.status_code == 200 and svg["Content-Type"] == "image/svg+xml"
    data = json.loads(signed_in.get(f"/s/{pk}/chart/{name}.json?{WEEK}").content)
    assert not data["empty"]


def test_the_chart_data(pk, signed_in):
    """Kinds by collaborators and others; merged pull requests by their reviews."""
    kinds = json.loads(signed_in.get(f"/s/{pk}/chart/reviews-kinds.json?{WEEK}").content)
    assert kinds["labels"] == ["approved", "changes requested", "commented", "dismissed or unknown"]
    assert [d["data"] for d in kinds["datasets"]] == [[1, 0, 1, 0], [1, 1, 0, 0]]
    merge = json.loads(signed_in.get(f"/s/{pk}/chart/reviews-merge.json?{WEEK}").content)
    assert merge["labels"] == ["0", "1", "2", "3", "4", "5+"]
    assert merge["datasets"][0]["data"] == [1, 0, 1, 0, 0, 0]
    time = json.loads(signed_in.get(f"/s/{pk}/chart/reviews-time.json?{WEEK}&by=week").content)
    assert time["x"].startswith("calendar week")


def test_the_page_is_in_the_menu(pk, signed_in):
    """Reviews follows Replies in the menu of the pages."""
    page = signed_in.get(f"/s/{pk}/reviews/").content.decode()
    assert page.index(f'href="/s/{pk}/replies/') < page.index(f'href="/s/{pk}/reviews/')


def test_visitors_see_public_repositories(pk, client):
    """A public repository has the page for everybody."""
    assert client.get("/s/o~r/reviews/").status_code == 200
    assert client.get(f"/s/{pk}/reviews/").status_code == 302


def test_the_page_in_german(pk, signed_in):
    """The texts of the page are translated."""
    page = signed_in.get(f"/s/{pk}/reviews/?{WEEK}", HTTP_ACCEPT_LANGUAGE="de").content.decode()
    assert "Reviews von Mitwirkenden" in page or "von Mitwirkenden" in page
