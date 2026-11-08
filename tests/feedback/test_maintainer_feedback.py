"""Cases the maintainer reported on real data of the live site.

The tests of this file are kept apart from the other tests on purpose: each one is a case that
a person found wrong on https://insight.pycal.org, with the rule they gave. The data are copied
from GitHub into the database by hand, with the times of the events as they happened, so that
the case stays tested even after the pull request changes on GitHub. When a person reports a
new case, add a test here with the address they gave, what was wrong and what is right.

The rules of the list of pull requests and issues (``/s/<scope>/items/``):

- The first response is the first comment or review by somebody else than the author and not
  by a bot. A merge responds as well, and so does a close by somebody else than the author.
- *waiting* marks only open items, and only while nobody of the status collaborator or higher
  (owner, member, collaborator) has commented or reviewed. A closed item waits no more.
"""

from datetime import UTC, datetime

import pytest
from django.contrib.auth.models import AnonymousUser

from community_insights.classify import Classifier
from community_insights.models import Event, Item, Repository
from community_insights.stats import items_in
from community_insights.sync import store_repository
from community_insights.tables.items import items_with_responses

from ..factories import AccessTokenFactory, ProjectFactory
from ..fakes import FakeClient, repo

pytestmark = pytest.mark.django_db
ICALENDAR = "collective/icalendar"


def at(text: str) -> datetime:
    """A time in UTC.

    Args:
        text: Such as ``2026-11-02 19:14:48``.

    Returns:
        The time.
    """
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


def pull_request(number, author, opened, events, state="open", merged=False, closer=""):
    """A pull request of collective/icalendar with its events, as GitHub had them.

    Args:
        number: Its number.
        author: Its author.
        opened: When it was opened, such as ``2026-11-02 19:14:48``.
        events: (kind, actor, association, is_bot, time, state of a review) of its events.
        state: ``open`` or ``closed``.
        merged: Whether it is merged.
        closer: Who merged or closed it, with the time: (login, time).

    Returns:
        The pull request.
    """
    repository, _ = Repository.objects.get_or_create(full_name=ICALENDAR)
    login, closed = closer or ("", None)
    item = Item.objects.create(
        repository=repository,
        kind=Item.PR,
        number=number,
        author=author,
        state=state,
        merged=merged,
        created_at=at(opened),
        updated_at=at(opened),
        closed_at=at(closed) if closed else None,
        merged_by=login if merged else "",
        closed_by=login,
        details=Item.DETAILS,
    )
    for kind, actor, association, is_bot, time, review in events:
        Event.objects.create(
            item=item,
            kind=kind,
            actor=actor,
            association=association,
            is_bot=is_bot,
            at=at(time),
            state=review,
        )
    return item


def first_response(number: int):
    """The item with its first response and whether it waits, as a visitor sees it.

    Args:
        number: The number of the pull request.

    Returns:
        The item of ``items_with_responses``.
    """
    found = items_with_responses(
        items_in(Repository.objects.filter(full_name=ICALENDAR)), Classifier(AnonymousUser())
    )
    return next(item for item in found if item.number == number)


def pr_2058():
    """Dependabot opened it; niccokunzmann merged it 2 h 17 min later, without a comment."""
    return pull_request(
        2058,
        "dependabot",
        "2026-11-02 19:14:48",
        [(Event.OPENED, "dependabot", "contributor", True, "2026-11-02 19:14:48", "")],
        state="closed",
        merged=True,
        closer=("niccokunzmann", "2026-11-02 21:32:14"),
    )


def test_2058_a_merge_is_a_response():
    """https://github.com/collective/icalendar/pull/2058

    Reported: the merged pull request was shown as *waiting 2h 17min*. A merge counts as a
    response: its first response is the merge, and a merged pull request waits no more.
    """
    pr_2058()
    item = first_response(2058)
    assert item.first_response_at == at("2026-11-02 21:32:14")
    assert not item.waiting


def test_2058_closing_by_somebody_else_is_a_response():
    """Same report: "so is closing the PR a response".

    A pull request closed without merging by somebody else than the author got its answer
    then. Closing their own pull request is no response: the author gave up, nobody answered.
    """
    pull_request(
        1,
        "kim",
        "2026-11-01 10:00:00",
        [],
        state="closed",
        closer=("niccokunzmann", "2026-11-01 12:00:00"),
    )
    pull_request(
        2, "kim", "2026-11-01 10:00:00", [], state="closed", closer=("kim", "2026-11-01 12:00:00")
    )
    assert first_response(1).first_response_at == at("2026-11-01 12:00:00")
    assert first_response(2).first_response_at is None
    assert not first_response(2).waiting, "closed: it waits no more"


def test_2057_a_review_is_a_response():
    """https://github.com/collective/icalendar/pull/2057

    Reported: "Clearly has a review - this does not count as waiting". The comment of the bot
    github-actions after 11 s does not count; the review of angatha (member) does.
    """
    pull_request(
        2057,
        "bohuis686-creator",
        "2026-11-02 15:48:59",
        [
            (Event.OPENED, "bohuis686-creator", "contributor", False, "2026-11-02 15:48:59", ""),
            (Event.COMMENT, "github-actions", "contributor", True, "2026-11-02 15:49:10", ""),
            (Event.REVIEW, "angatha", "member", False, "2026-11-05 08:40:06", "changes_requested"),
            (Event.COMMENT, "bohuis686-creator", "contributor", False, "2026-11-05 16:06:12", ""),
            (Event.REVIEW, "angatha", "member", False, "2026-11-06 07:10:53", "commented"),
            (Event.COMMENT, "angatha", "member", False, "2026-11-06 07:13:31", ""),
            (Event.REVIEW, "angatha", "member", False, "2026-11-06 07:14:02", "dismissed"),
        ],
    )
    item = first_response(2057)
    assert item.first_response_at == at("2026-11-05 08:40:06")
    assert not item.waiting


def test_2050_a_review_comment_of_a_member_ends_the_waiting():
    """https://github.com/collective/icalendar/pull/2050

    Given with the rule: "only open PRs should be labelled as waiting and only if they are
    still waiting for a response from a collaborator or higher". Three comments of
    github-actions and one of the author come first; the review of angatha (member) after
    four days answers it, so the open pull request does not wait.
    """
    pull_request(
        2050,
        "AthosTomich",
        "2026-11-01 09:05:39",
        [
            (Event.OPENED, "AthosTomich", "contributor", False, "2026-11-01 09:05:39", ""),
            (Event.COMMENT, "github-actions", "contributor", True, "2026-11-01 09:05:49", ""),
            (Event.COMMENT, "github-actions", "contributor", True, "2026-11-01 09:05:50", ""),
            (Event.COMMENT, "github-actions", "contributor", True, "2026-11-01 09:05:52", ""),
            (Event.COMMENT, "AthosTomich", "contributor", False, "2026-11-01 09:11:09", ""),
            (Event.REVIEW, "angatha", "member", False, "2026-11-05 08:13:06", "commented"),
        ],
    )
    item = first_response(2050)
    assert item.first_response_at == at("2026-11-05 08:13:06")
    assert not item.waiting


def test_only_open_pull_requests_wait_for_a_collaborator():
    """The same rule, for the cases around it.

    An open pull request that only an external person commented on has a first response, but
    still waits for a collaborator or higher. One that only the author and a bot commented on
    waits. A closed one without any response does not wait: it shows *no response*.
    """
    external = [(Event.COMMENT, "dave", "contributor", False, "2026-11-01 11:00:00", "")]
    pull_request(1, "kim", "2026-11-01 10:00:00", external)
    bot = [(Event.COMMENT, "github-actions", "none", True, "2026-11-01 10:00:10", "")]
    pull_request(2, "kim", "2026-11-01 10:00:00", bot)
    pull_request(
        3, "kim", "2026-11-01 10:00:00", [], state="closed", closer=("", "2026-11-03 10:00:00")
    )
    assert first_response(1).first_response_at is not None and first_response(1).waiting
    assert first_response(2).first_response_at is None and first_response(2).waiting
    assert first_response(3).first_response_at is None and not first_response(3).waiting


def test_the_page_shows_waiting_only_for_open_pull_requests(client):
    """What the page shows for 2058, 2057 and a pull request nobody answered yet."""
    pr_2058()
    test_2057_a_review_is_a_response()
    pull_request(2052, "guan5313", "2026-11-01 10:00:00", [])
    page = client.get("/s/collective~icalendar/items/").content.decode()

    def cell(number):
        """The row of a pull request.

        Args:
            number: Its number.

        Returns:
            The HTML of its row.
        """
        start = page.index(f'/pull/{number}"')
        return page[start : page.index("</tr>", start)]

    assert "waiting" not in cell(2058) and "2h 17min" in cell(2058)
    assert "waiting" not in cell(2057) and "2d 16h" in cell(2057)
    assert "waiting" in cell(2052)


def test_update_keeps_the_filters_of_the_table(user, signed_in, monkeypatch):
    """https://insight.pycal.org/s/collective~icalendar/items/

    Reported: "Clicking the update button on collective~icalendar/items/ should keep the
    filters of the table intact". The button returns to the whole address, with its filters,
    and so does the page Fetch reached from its drop-down.
    """
    repository = store_repository(repo(ICALENDAR, 5))
    project = ProjectFactory(user=user, target=ICALENDAR, repositories=[repository])
    AccessTokenFactory(user=user)
    monkeypatch.setattr("community_insights.github.Client", lambda *a, **k: FakeClient())
    address = f"/s/{project.pk}/items/?kind=pr&state=closed&state=merged&responded=false"
    page = signed_in.get(address).content.decode()
    assert f'name="next" value="{address.replace("&", "&amp;")}"' in page
    response = signed_in.post(f"/s/{project.pk}/fetch/", {"action": "now", "next": address})
    assert response.status_code == 302 and response["Location"] == address
    chosen = signed_in.get(f"/s/{project.pk}/fetch/", {"next": address}).content.decode()
    assert f'name="next" value="{address.replace("&", "&amp;")}"' in chosen, "the page Fetch"


def test_2058_every_page_sees_the_same_response():
    """Reported: "It is a common mental model of what counts as a response. That does not differ
    per page."

    The merge of 2058 by niccokunzmann, after 2 h 17 min 26 s, is its first response on every
    page: the list of pull requests and issues, the response times of each class, the download,
    the response time of niccokunzmann as a contributor and their responses by month. It is no
    feedback that the author has to reply to on the page Replies.
    """
    from community_insights import export, stats

    pr_2058()
    seconds = 2 * 3600 + 17 * 60 + 26
    repositories = Repository.objects.filter(full_name=ICALENDAR)
    visitor = Classifier(AnonymousUser())
    assert first_response(2058).response.total_seconds() == seconds, "the list"
    entry = stats.response_entries(repositories, visitor)[Item.PR][0]
    assert entry == {stats.FIRST: seconds, "collaborator or higher": seconds}, "response times"
    row = export.responses(repositories, visitor, ["collaborator or higher"])[0]
    assert row["seconds_any"] == seconds and row["seconds_collaborator_or_higher"] == seconds
    people = {p.login: p for p in stats.contributors(repositories, visitor)}
    assert people["niccokunzmann"].delays == [seconds], "hours_to_respond of the contributor"
    by_month = stats.responses_by_month(repositories, "niccokunzmann", UTC)
    assert by_month == {(2026, 11): [seconds]}, "the page of the person"
    pull = stats.pull_replies(repositories, visitor)[0]
    assert pull.first_feedback is None, "a merge needs no reply"
