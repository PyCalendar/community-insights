"""The checkbox "Count drafts as open pull requests" on Replies, the person pages and badges."""

import json
import re

import pytest

from community_insights import stats
from community_insights.models import Item, Repository

pytestmark = pytest.mark.django_db


@pytest.fixture
def draft(replied):
    """An open pull request with feedback its author did not answer, made a draft.

    Returns:
        The pull request (``stats.PullReply``).
    """
    pulls = stats.pull_replies(Repository.objects.all())
    found = next(p for p in pulls if p.state == "open" and p.first_feedback and not p.answered)
    Item.objects.filter(kind=Item.PR, number=found.number).update(draft=True)
    return found


def text(client, path: str) -> str:
    """A page as text.

    Args:
        client: The client.
        path: The address.

    Returns:
        The HTML.
    """
    response = client.get(path)
    assert response.status_code == 200, path
    return response.content.decode()


def test_the_checkbox_on_replies(draft, client):
    """Off by default; on with drafts=1; the other parameters of the page stay."""
    page = text(client, "/s/o~r/replies/?last=30&order=person")
    box = re.search(r"<form[^>]*data-drafts>.*?</form>", page, re.S).group(0)
    assert 'name="drafts" value="1" data-submit-on-change' in box, "not checked"
    assert '<input type="hidden" name="last" value="30">' in box
    assert '<input type="hidden" name="order" value="person">' in box
    assert "Count drafts as open pull requests" in box
    checked = text(client, "/s/o~r/replies/?drafts=1")
    assert 'value="1" checked data-submit-on-change' in checked


def test_the_draft_is_left_out_of_the_replies(draft, client):
    """The pull request of the draft is in the table only with drafts=1."""
    person = f"/s/o~r/replies/{draft.author}/"
    assert f"pull/{draft.number}" not in text(client, person)
    assert f"pull/{draft.number}" in text(client, person + "?drafts=1")


def test_links_carry_the_choice(draft, client):
    """The menu and the people of the page keep drafts=1, so other pages count the same."""
    page = text(client, "/s/o~r/replies/?drafts=1")
    assert 'href="/s/o~r/people/' in page
    assert re.search(r'href="/s/o~r/people/[^"]+/\?drafts=1"', page)
    assert 'href="/s/o~r/trends/?drafts=1"' in page


def test_the_person_page_counts_open_drafts_apart(draft, client):
    """By default: "and 1 open draft"; with drafts=1 it is one of the open ones."""
    page = text(client, f"/s/o~r/people/{draft.author}/")
    assert "and 1 open draft" in page
    assert "data-drafts-left-out" not in text(client, f"/s/o~r/people/{draft.author}/?drafts=1")
    assert 'id="drafts-toggle"' in page


def test_the_badge_follows_the_choice(draft, client):
    """The badge page links the badge with drafts=1; the badge counts them then."""
    login = draft.author
    page = text(client, f"/s/o~r/replies/{login}/badge/?drafts=1")
    assert f"/badge/s/o~r/replies/{login}.svg?drafts=1" in page
    without = json.loads(client.get(f"/badge/s/o~r/replies/{login}.json").content)
    including = json.loads(client.get(f"/badge/s/o~r/replies/{login}.json?drafts=1").content)
    assert draft.number not in without["not_replied_open"].get("o/r", [])
    assert draft.number in including["not_replied_open"]["o/r"]
    assert including["page"].endswith("?drafts=1")
