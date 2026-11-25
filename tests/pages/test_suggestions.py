"""The pages and badges of suggestions: by project, person and pull request, and the table."""

import re

import pytest

from community_insights.models import Item, Project, Suggestion
from community_insights.sync import store_repository

from ..data import read_repository
from ..fakes import FakeClient, item, node, repo
from ..statistics.test_suggestions import comment, thread

pytestmark = pytest.mark.django_db


def reviewed(number, author, *threads, state="OPEN", merged=False):
    """A pull request with a review of bob and review threads.

    Args:
        number: Its number.
        author: Its author.
        *threads: Its review threads.
        state: ``OPEN`` or ``CLOSED``.
        merged: Whether it was merged.

    Returns:
        The pull request as GitHub answers it.
    """
    data = item(
        number,
        author,
        "2026-01-05T09:00:00Z",
        reviews=[node("bob", "2026-01-05T10:00:00Z", "MEMBER", key="submittedAt")],
        state=state,
        merged=merged,
    )
    data["reviewThreads"] = {"nodes": list(threads)}
    data["commits"] = {"nodes": []}
    return data


def suggestion_client() -> FakeClient:
    """A fake GitHub: #1 of ann applied and open, #2 of ann unknown, #3 of cid applied,
    #4 of dot without a review, so its threads are not read; #5 of eve merged and #6 of eve
    closed, with an open suggestion each.

    Returns:
        The fake.
    """
    unreviewed = item(4, "dot", "2026-01-05T09:00:00Z", reviews=[])
    unreviewed["reviewThreads"] = {"nodes": [thread(comment("bob", 1, number=41))]}
    return FakeClient(
        prs=[
            reviewed(
                1,
                "ann",
                thread(
                    comment("bob", 1, number=11), comment("ann", 3, "Done in 3f2c9ab.", number=12)
                ),
                thread(comment("bob", 4, number=13)),
            ),
            reviewed(2, "ann", thread(comment("bob", 5, number=21), resolved_by="ann")),
            reviewed(3, "cid", thread(comment("bob", 6, number=31), resolved_by="bob")),
            unreviewed,
            reviewed(5, "eve", thread(comment("bob", 7, number=51)), state="CLOSED", merged=True),
            reviewed(6, "eve", thread(comment("bob", 8, number=61)), state="CLOSED"),
        ]
    )


@pytest.fixture
def suggested(user):
    """The public repository o/r, read with its suggestions, in a project of the user.

    Returns:
        The project.
    """
    repository = store_repository(repo("o/r", 5))
    read_repository(suggestion_client(), repository)
    project = Project.objects.create(user=user, target="o/r")
    project.repositories.add(repository)
    return project


def text(client, path: str) -> str:
    """A page as text.

    Args:
        client: The client.
        path: The address.

    Returns:
        The HTML.
    """
    response = client.get(path)
    assert response.status_code == 200, (path, response.status_code)
    return response.content.decode()


def test_the_fetch_reads_the_suggestions(suggested):
    """Of the pull requests with a review; #4 has none, so its threads are not read."""
    found = dict(Suggestion.objects.values_list("comment_id", "status"))
    assert found == {
        11: "applied",
        13: "open",
        21: "unknown",
        31: "applied",
        51: "open",
        61: "open",
    }
    assert Item.objects.get(number=4).threads_updated_at is None


def test_the_suggestions_of_the_project_grouped_by_pull_request(suggested, client):
    """The newest suggestion first, of open pull requests; each pull request with its badge."""
    page = text(client, "/s/o~r/suggestions/")
    assert re.findall(r'data-pr="o/r#(\d+)"', page) == ["3", "2", "1"]
    first = re.search(r'<details[^>]*data-pr="o/r#1".*?</details>', page, re.S).group(0)
    assert ">suggestions</span>" in first and ">1/2</span>" in first and "mini-badge-red" in first
    assert re.findall(r'<tr data-status="(\w+)"', first) == ["open", "applied"]
    assert 'href="/s/o~r/suggestions/o~r/1/"' in first, "the badge leads to the pull request"
    assert 'href="/s/o~r/people/ann/suggestions/"' in first
    assert "a reply names a commit" in first


def test_the_columns_of_a_suggestion(suggested, client):
    """The pull request and the time link the suggestion; the last in the thread its message."""
    page = text(client, "/s/o~r/suggestions/o~r/1/")
    row = re.search(r'<tr data-status="applied">.*?</tr>', page, re.S).group(0)
    assert row.count('href="https://github.com/o/r/pull/1#discussion_r11"') == 3
    assert "ago" in row and "2026-01-05" in row
    assert 'href="https://github.com/o/r/pull/1#discussion_r12">ann</a>' in row, "the handle only"
    assert "author:" not in row and "suggester:" not in row


def test_the_filter_switches_statuses_on_and_off(suggested, client):
    """Only open ones; none at all; the summaries still count all."""
    page = text(client, "/s/o~r/suggestions/?filtered=1&status=open")
    assert re.findall(r'data-pr="o/r#(\d+)"', page) == []
    assert 'name="state" value="open" checked' not in page, "the form was sent without a state"
    page = text(client, "/s/o~r/suggestions/?filtered=1&status=open&state=open")
    assert re.findall(r'data-pr="o/r#(\d+)"', page) == ["1"]
    assert 'name="status" value="open" checked' in page
    assert 'name="status" value="applied" checked' not in page
    assert ">1/2</span>" in page, "the badge counts all suggestions"
    assert "No suggestions to show in this time." in text(client, "/s/o~r/suggestions/?filtered=1")


def test_the_suggestions_to_a_person(suggested, client):
    """Only the pull requests of ann, with her badge."""
    page = text(client, "/s/o~r/people/ann/suggestions/")
    assert re.findall(r'data-pr="o/r#(\d+)"', page) == ["2", "1"]
    assert "Pull requests:" in page, "the states can be chosen"
    assert '<img src="/badge/s/o~r/suggestions/ann.svg"' in page


def test_a_pull_request_that_does_not_exist(suggested, client):
    """A number without a pull request is a missing page."""
    assert client.get("/s/o~r/suggestions/o~r/99/").status_code == 404


def test_the_badges_of_suggestions(suggested, client):
    """Of a person and of a pull request: public and with the secret token."""
    ann = client.get("/badge/s/o~r/suggestions/ann.json").json()
    assert (ann["message"], ann["status"], ann["total"]) == ("1/3 suggestions applied", "red", 3)
    cid = client.get("/badge/s/o~r/suggestions/cid.json").json()
    assert cid["status"] == "green"
    pr = client.get("/badge/s/o~r/pull/o~r/2/suggestions.json").json()
    assert (pr["label"], pr["message"], pr["status"]) == ("suggestions", "0/1", "yellow")
    numbered = client.get("/badge/s/o~r/pull/o~r/2/suggestions.json?number=1").json()
    assert (numbered["label"], numbered["message"]) == ("PR #2 suggestions", "0/1")
    numbered = client.get(f"/badge/{suggested.badge_token}/pull/o~r/2/suggestions.json?number=1")
    assert numbered.json()["label"] == "PR #2 suggestions"
    nobody = client.get("/badge/s/o~r/suggestions/nobody.json").json()
    assert (nobody["message"], nobody["status"]) == ("no suggestions", None)
    svg = client.get("/badge/s/o~r/suggestions/ann.svg")
    assert svg["Content-Type"].startswith("image/svg+xml")
    token = suggested.badge_token
    assert client.get(f"/badge/{token}/suggestions/ann.json").json()["status"] == "red"
    assert client.get(f"/badge/{token}/pull/o~r/3/suggestions.json").json()["status"] == "green"
    assert client.get(f"/badge/s/{suggested.pk}/suggestions/ann.svg").status_code == 404
    assert client.get("/badge/s/o~r/suggestions/ann.gif").status_code == 404


def test_the_table_of_pull_requests_has_their_badges(suggested, signed_in):
    """The column Suggestions addressed: the badge of each pull request with suggestions."""
    page = text(signed_in, f"/s/{suggested.pk}/items/")
    assert "Suggestions addressed" in page
    assert 'href="/s/o~r/suggestions/o~r/2/"' in page
    assert ">suggestions</span>" in page and ">0/1</span>" in page


def test_the_badges_page_has_both_badges(suggested, client):
    """/s/<scope>/badges/<login>/ has the badge of replies and of suggestions."""
    page = text(client, "/s/o~r/badges/ann/")
    assert "Badges of ann" in page and "data-suggestion-badge" in page
    assert 'data-share-image="http://testserver/badge/s/o~r/suggestions/ann.svg"' in page
    assert 'data-share-link="http://testserver/s/o~r/people/ann/suggestions/"' in page


def test_the_old_address_of_the_badge_leads_to_the_badges(suggested, client):
    """/s/<scope>/replies/<login>/badge/ moved, with its parameters."""
    response = client.get("/s/o~r/replies/ann/badge/?drafts=1")
    assert response.status_code == 301
    assert response["Location"] == "/s/o~r/badges/ann/?drafts=1"


def test_the_menus_offer_the_suggestions(suggested, client):
    """The pages of the project and of a person have Suggestions."""
    page = text(client, "/s/o~r/")
    assert 'href="/s/o~r/suggestions/"' in page
    person = text(client, "/s/o~r/people/ann/")
    assert 'href="/s/o~r/people/ann/suggestions/"' in person


def test_the_pages_are_split(suggested, client, monkeypatch):
    """More pull requests than fit on a page: the next page."""
    from community_insights.views import suggestions

    monkeypatch.setattr(suggestions, "PULLS_PER_PAGE", 2)
    first = text(client, "/s/o~r/suggestions/")
    assert re.findall(r'data-pr="o/r#(\d+)"', first) == ["3", "2"]
    assert "data-pager" in first and 'href="?page=2"' in first
    second = text(client, "/s/o~r/suggestions/?page=2")
    assert re.findall(r'data-pr="o/r#(\d+)"', second) == ["1"]


def test_links_to_github_have_its_mark(suggested, client):
    """The style puts the mark of GitHub in front of every link to GitHub."""
    from pathlib import Path

    style = (Path(__file__).parents[2] / "static" / "style.css").read_text()
    assert 'a[href^="https://github.com"]::before' in style
    assert 'url("img/github-mark.svg")' in style


def test_a_changed_pull_request_is_read_again(suggested):
    """After a change, the threads are read again: the open suggestion was applied."""
    client = suggestion_client()
    client.prs[0]["reviewThreads"]["nodes"][1]["comments"]["nodes"].append(
        comment("ann", 9, "Applied in 9c8b7a6.", number=14)
    )
    client.prs[0]["updatedAt"] = "2026-02-01T10:00:00Z"
    read_repository(client, suggested.repositories.get())
    assert Suggestion.objects.get(comment_id=13).status == "applied"
    assert Suggestion.objects.filter(comment_id=11).exists(), "the others are read again, too"


def test_an_unchanged_pull_request_is_not_read_again(suggested):
    """The threads of pull requests that did not change are not asked for again."""
    from asgiref.sync import async_to_sync

    from community_insights.sync import Syncer

    client = suggestion_client()
    message = async_to_sync(Syncer(client).sync_threads)(suggested.repositories.get())
    assert message == "suggestions of 0 pull requests read: 0" and client.requests == 0


def test_the_states_of_the_pull_requests(suggested, client):
    """Open ones at first; merged and closed ones when chosen, the newest first."""
    page = text(client, "/s/o~r/suggestions/")
    assert 'name="state" value="open" checked' in page
    assert 'name="state" value="merged" checked' not in page
    assert "o/r#5" not in page and "o/r#6" not in page
    every = "?filtered=1&status=open&status=applied&status=unknown"
    merged = text(client, f"/s/o~r/suggestions/{every}&state=merged")
    assert re.findall(r'data-pr="o/r#(\d+)"', merged) == ["5"]
    closed = text(client, f"/s/o~r/suggestions/{every}&state=closed")
    assert re.findall(r'data-pr="o/r#(\d+)"', closed) == ["6"]
    both = text(client, f"/s/o~r/suggestions/{every}&state=closed&state=merged&state=open")
    assert re.findall(r'data-pr="o/r#(\d+)"', both) == ["6", "5", "3", "2", "1"]


def test_the_page_of_a_pull_request_shows_it_in_any_state(suggested, client):
    """A merged pull request has its suggestions on its page; no choice of states there."""
    page = text(client, "/s/o~r/suggestions/o~r/5/")
    assert re.findall(r'data-pr="o/r#(\d+)"', page) == ["5"]
    assert "data-state-filter" not in page


def test_the_badge_of_a_pull_request_can_start_with_its_number(suggested, client):
    """The checkbox number=1 changes the badge and its code."""
    page = text(client, "/s/o~r/suggestions/o~r/2/")
    assert '<img src="/badge/s/o~r/pull/o~r/2/suggestions.svg"' in page
    assert 'id="number-toggle" name="number" value="1" data-submit-on-change' in page
    assert 'data-share-image="http://testserver/badge/s/o~r/pull/o~r/2/suggestions.svg"' in page
    assert 'data-share-alt="suggestions"' in page and 'data-share="markdown"' in page
    assert 'href="http://testserver/badge/s/o~r/pull/o~r/2/suggestions.json"' in page
    numbered = text(client, "/s/o~r/suggestions/o~r/2/?number=1")
    assert '<img src="/badge/s/o~r/pull/o~r/2/suggestions.svg?number=1"' in numbered
    assert 'value="1" checked' in numbered and 'data-share-alt="PR #2 suggestions"' in numbered
    png = text(client, "/s/o~r/suggestions/o~r/2/?number=1&format=png")
    assert (
        'data-share-image="http://testserver/badge/s/o~r/pull/o~r/2/suggestions.png?number=1"'
        in png
    )
    assert 'href="?number=1&amp;format=svg"' in png, "the format keeps the number"


def test_the_newest_suggestion_of_a_pull_request_comes_first(suggested, client):
    """Within a pull request: newest first, whatever the status."""
    page = text(client, "/s/o~r/suggestions/o~r/1/")
    assert re.findall(r'discussion_r(\d+)">#1', page) == ["13", "11"]
