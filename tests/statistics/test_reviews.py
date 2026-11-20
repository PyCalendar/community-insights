"""The reviews of pull requests: by collaborators and others, kinds, trend, until merged."""

from datetime import UTC, datetime

import pytest

from community_insights import stats
from community_insights.models import Repository
from community_insights.stats.review_numbers import by_collaborator, kind_of
from community_insights.sync import store_repository

from ..data import read_repository
from ..fakes import FakeClient, item, node, repo

pytestmark = pytest.mark.django_db

SINCE = datetime(2026, 1, 8, tzinfo=UTC)  # a week
UNTIL = datetime(2026, 1, 15, tzinfo=UTC)
NOW = datetime(2026, 2, 1, tzinfo=UTC)


def review(login, day, association="MEMBER", state="APPROVED", hour=12):
    """A review on a day of January 2026.

    Args:
        login: The reviewer.
        day: The day.
        association: The status of the reviewer.
        state: The kind of review.
        hour: The hour.

    Returns:
        The review as GitHub answers it.
    """
    at = f"2026-01-{day:02d}T{hour:02d}:00:00Z"
    return node(login, at, association, key="submittedAt", state=state)


@pytest.fixture
def reviewed(db):
    """Pull requests with reviews in the week and before it.

    #1 by ann, merged on the 10th: maint approves on the 9th, out (CONTRIBUTOR) asks for
    changes on the 9th, ann reviews her own on the 9th, a bot comments on the 9th, maint
    comments on the 12th after the merge. #2 by bob, open: maint comments on the 3rd
    (before the week), lea (NONE) approves on the 11th. #3 by cy, merged on the 13th
    without a review.
    """
    repository = store_repository(repo("o/r"))
    one = item(
        1,
        "ann",
        "2026-01-08T09:00:00Z",
        reviews=[
            review("maint", 9),
            review("out", 9, "CONTRIBUTOR", "CHANGES_REQUESTED", 13),
            review("ann", 9, "CONTRIBUTOR", "COMMENTED", 14),
            node("ci[bot]", "2026-01-09T15:00:00Z", key="submittedAt", typename="Bot"),
            review("maint", 12, state="COMMENTED"),
        ],
        state="CLOSED",
        merged=True,
        closer="maint",
        updated="2026-01-10T12:00:00Z",
    )
    two = item(
        2,
        "bob",
        "2026-01-02T09:00:00Z",
        reviews=[review("maint", 3, state="COMMENTED"), review("lea", 11, "NONE")],
    )
    three = item(
        3,
        "cy",
        "2026-01-12T09:00:00Z",
        reviews=[],
        state="CLOSED",
        merged=True,
        closer="maint",
        updated="2026-01-13T12:00:00Z",
    )
    read_repository(FakeClient(prs=[one, two, three]), repository)
    return Repository.objects.all()


def test_the_reviews_of_the_week(reviewed):
    """Bots and the author are left out; collaborators and others apart; the week before."""
    found = stats.review_numbers(reviewed, SINCE, UNTIL, NOW)
    assert found.total == stats.Change(4, 1), "maint 2, out, lea; maint on the 3rd before"
    assert found.collaborators == stats.Change(2, 1)
    assert found.others == stats.Change(2, 0)
    assert found.reviewers == 3


def test_the_kinds_of_review(reviewed):
    """Approved, changes requested, commented: by collaborators and by others."""
    found = stats.review_numbers(reviewed, SINCE, UNTIL, NOW)
    assert found.kinds == {
        "approved": [1, 1],
        "changes_requested": [0, 1],
        "commented": [1, 0],
        "other": [0, 0],
    }


def test_the_reviews_until_merged(reviewed):
    """#1 had two reviews before its merge (the comment after it does not count), #3 none."""
    found = stats.review_numbers(reviewed, SINCE, UNTIL, NOW)
    assert sorted(found.merged) == [0, 2]
    assert found.histogram == [1, 0, 1, 0, 0, 0]
    assert (found.median, found.mean, found.without) == (1.0, 1.0, 1)


def test_nothing_merged():
    """Without merged pull requests: no median."""
    found = stats.review_numbers(Repository.objects.none(), SINCE, UNTIL, NOW)
    assert found.merged == [] and found.median is None and found.mean is None


def test_all_time_has_nothing_before(reviewed):
    """Without a start, nothing is compared."""
    assert stats.review_numbers(reviewed, None, None, NOW).total == stats.Change(5, None)


def test_the_reviews_per_bar(reviewed):
    """Per day of the week, by collaborators and by others; the part of each bar."""
    found = stats.review_series(reviewed, SINCE, UNTIL, NOW, UTC)
    assert found["size"] == "day" and len(found["labels"]) == 7
    assert found["collaborators"] == [0, 1, 0, 0, 1, 0, 0]
    assert found["others"] == [0, 1, 0, 1, 0, 0, 0]
    assert found["total"] == [
        a + b for a, b in zip(found["collaborators"], found["others"], strict=True)
    ]
    assert found["exposure"] == [1.0] * 7
    months = stats.review_series(reviewed, SINCE, UNTIL, NOW, UTC, "month")
    assert months["labels"] == ["2026-01"] and months["total"] == [4]


def test_no_reviews_no_bars():
    """Without reviews there is nothing to draw."""
    found = stats.review_series(Repository.objects.none(), None, None, NOW, UTC)
    assert found["labels"] == [] and found["total"] == []


@pytest.mark.parametrize(
    ("association", "collaborator"),
    [
        ("OWNER", True),
        ("member", True),
        ("COLLABORATOR", True),
        ("CONTRIBUTOR", False),
        ("FIRST_TIME_CONTRIBUTOR", False),
        ("NONE", False),
        ("", False),
    ],
)
def test_who_is_a_collaborator(association, collaborator):
    """Owners, members and collaborators, as GitHub names their status."""
    assert by_collaborator(association) is collaborator


def test_the_kinds():
    """Dismissed and unknown reviews are other ones."""
    assert [
        kind_of(s) for s in ("approved", "changes_requested", "commented", "dismissed", "")
    ] == ["approved", "changes_requested", "commented", "other", "other"]


def test_a_merged_pull_request_without_its_time_is_left_out(reviewed):
    """GitHub always names the time of a merge; one without it cannot be placed."""
    from community_insights.models import Item

    Item.objects.filter(number=3).update(closed_at=None)
    found = stats.review_numbers(reviewed, None, None, NOW)
    assert found.merged == [2]
