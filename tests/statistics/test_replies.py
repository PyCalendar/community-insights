"""Whether the authors of pull requests answered the feedback they got."""

from datetime import UTC, datetime

import pytest
from django.contrib.auth.models import AnonymousUser

from community_insights import stats
from community_insights.classify import Classifier
from community_insights.models import Item, ItemCommit
from community_insights.sync import read_repository

from ..data import replies_client
from ..fakes import item, node

pytestmark = pytest.mark.django_db


def by_login(found) -> dict:
    """The results by the handle of each person.

    Args:
        found: The results of ``stats.replies``.

    Returns:
        The results by login.
    """
    return {person.login: person for person in found}


def test_who_answered_and_who_did_not(replied):
    """ann answered, ben and fay left their only one, cid one of three."""
    found = by_login(
        stats.replies(replied["project"].repositories.all(), Classifier(replied["user"]))
    )
    assert found["ann"].status == "green"
    assert (found["ann"].with_feedback, found["ann"].unanswered) == (2, {})
    assert found["ben"].status == "yellow" and found["ben"].unanswered == {"o/r": [3]}
    assert "fay" not in found, "she closed her only pull request herself"
    assert found["cid"].status == "red"
    assert found["cid"].unanswered == {"o/r": [4]}, "the commit of maint is no answer of cid"
    assert (found["cid"].prs, found["cid"].with_feedback, found["cid"].answered) == (3, 2, 1)


def test_who_is_not_listed(replied):
    """Without feedback, bots and comments of bots do not count."""
    found = by_login(
        stats.replies(replied["project"].repositories.all(), Classifier(replied["user"]))
    )
    assert "dot" not in found, "no feedback"
    assert "dependabot[bot]" not in found, "a bot opened it"
    assert "eve" not in found, "coveralls is a bot of the classes"
    assert "maint" not in found


def test_bots_by_handle_count_without_classes(replied):
    """Without a classifier, only GitHub knows the bots: coveralls gives feedback to eve."""
    found = by_login(stats.replies(replied["project"].repositories.all()))
    assert found["eve"].status == "yellow"


def test_closed_by_others(replied):
    """maint closed the pull request of ben without merging; fay closed her own."""
    found = by_login(
        stats.replies(replied["project"].repositories.all(), Classifier(replied["user"]))
    )
    assert found["ben"].closed_by_others == 1
    assert Item.objects.get(number=3, kind=Item.PR).closed_by == "maint"
    assert Item.objects.get(number=1, kind=Item.PR).closed_by == "", "still open"


def test_a_pull_request_closed_by_its_author_does_not_count(replied):
    """fay closed PR 10 herself: it needs no answer, and she is not listed."""
    pulls = stats.pull_replies(replied["project"].repositories.all(), login="fay")
    assert [(p.number, p.closed_by_author, p.counted, p.unanswered) for p in pulls] == [
        (10, True, False, False)
    ]
    assert stats.replies(replied["project"].repositories.all(), login="fay") == []


def test_the_total_counts_every_pull_request(replied):
    """ann: 2 open, 1 merged; PRs merged is 1/3."""
    ann = by_login(stats.replies(replied["project"].repositories.all()))["ann"]
    assert (ann.merged, ann.total) == (1, 3)


def test_the_order_puts_open_pull_requests_without_reply_first(replied):
    """An open one without reply first (bob's #12, cid's #4); then 0/1 before 1/2 before 2/2;
    with the same share, more feedback first: 2/2 before 1/1."""
    found = stats.replies(replied["project"].repositories.all(), Classifier(replied["user"]))
    assert [(p.login, p.answered, p.with_feedback) for p in found] == [
        ("bob", 0, 1),
        ("cid", 1, 2),
        ("ben", 0, 1),
        ("ann", 2, 2),
        ("Bobby", 1, 1),
        ("rae", 1, 1),
    ]


def test_one_person_in_any_case(replied):
    """``login`` chooses one person exactly, in any case: bob is not Bobby."""
    repositories = replied["project"].repositories.all()
    assert [p.login for p in stats.replies(repositories, login="BOB")] == ["bob"]
    assert [p.login for p in stats.replies(repositories, login="bobby")] == ["Bobby"]
    assert stats.replies(repositories, login="nobody") == []


def test_the_time_range_of_the_pull_requests(replied):
    """Only pull requests created in the time range count."""
    repositories = replied["project"].repositories.all()
    march = datetime(2026, 3, 1, tzinfo=UTC)
    assert {p.login for p in stats.replies(repositories, since=march)} == {"bob", "Bobby"}
    assert "bob" not in {p.login for p in stats.replies(repositories, until=march)}


def test_the_last_commits_are_stored_and_replaced(replied):
    """The commits of a pull request are read again with each change."""
    pr = Item.objects.get(number=4, kind=Item.PR)
    assert sorted(pr.commits.values_list("actor", flat=True)) == ["cid", "maint"]
    client = replies_client()
    client.prs[3] = item(
        4,
        "cid",
        "2026-01-05T10:00:00Z",
        comments=[node("maint", "2026-01-05T12:00:00Z", "MEMBER")],
        reviews=[],
        commits=[("cid", "2026-01-08T09:00:00Z")],
        updated="2026-04-01T10:00:00Z",
    )
    read_repository(client, replied["repository"])
    assert list(pr.commits.values_list("actor", flat=True)) == ["cid"]
    found = by_login(stats.replies(replied["project"].repositories.all(), Classifier(None)))
    assert found["cid"].status == "green", "the new commit answers the comment"


def test_pull_requests_read_without_commits(replied):
    """bob's pull request was read without commits: an answer by a commit is not seen."""
    assert stats.commits_unread(replied["project"].repositories.all()) == 1
    assert ItemCommit.objects.filter(item__number=12).count() == 0


def test_a_merged_pull_request_needs_no_answer(world):
    """bob's only pull request with feedback was merged: nobody is listed."""
    repositories = world["project"].repositories.all()
    assert stats.replies(repositories, Classifier(AnonymousUser())) == []


def test_merged_pull_requests_are_left_out(replied):
    """ann did not answer the comment on PR 13, but it was merged: she stays green."""
    ann = by_login(stats.replies(replied["project"].repositories.all(), Classifier(None)))["ann"]
    assert (ann.prs, ann.with_feedback, ann.status, ann.merged) == (2, 2, "green", 1)


def test_an_approval_needs_no_reply(replied):
    """gil only got an approval: nothing to reply to, so gil is not listed."""
    from community_insights.models import Event

    assert Event.objects.get(item__number=14, kind=Event.REVIEW).state == Event.APPROVED
    pulls = stats.pull_replies(replied["project"].repositories.all(), login="gil")
    assert [(p.number, p.first_feedback, p.answered) for p in pulls] == [(14, None, None)]
    assert stats.replies(replied["project"].repositories.all(), login="gil") == []


def test_a_reply_to_a_review_comment_is_a_reply(replied):
    """rae answered the requested changes in the review thread: GitHub keeps that as her
    review, read with the reviews; it counts as her reply."""
    rae = by_login(stats.replies(replied["project"].repositories.all()))["rae"]
    assert (rae.with_feedback, rae.answered, rae.status) == (1, 1, "green")


def test_a_comment_after_an_approval_needs_a_reply(replied):
    """An approval and then a comment: the comment is the feedback."""
    client = replies_client()
    client.prs[13] = item(
        14,
        "gil",
        "2026-01-05T10:00:00Z",
        comments=[node("maint", "2026-01-05T14:00:00Z", "MEMBER")],
        reviews=[
            node("maint", "2026-01-05T12:00:00Z", "MEMBER", key="submittedAt", state="APPROVED")
        ],
        commits=[("gil", "2026-01-05T13:00:00Z")],
        updated="2026-04-01T10:00:00Z",
    )
    read_repository(client, replied["repository"])
    gil = stats.pull_replies(replied["project"].repositories.all(), login="gil")[0]
    assert gil.first_feedback.hour == 14 and gil.answered is False, "the commit came before"
