"""The checkbox "Commits count as a reply" on Replies, the person pages and the badges."""

import re

import pytest

pytestmark = pytest.mark.django_db


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


def test_the_checkbox_is_off_by_default(replied, client):
    """Only comments answer by default; commits=1 checks the box."""
    page = text(client, "/s/o~r/replies/")
    box = re.search(r"<form[^>]*data-reply-options>.*?</form>", page, re.S).group(0)
    assert 'name="commits" value="1" data-submit-on-change' in box
    assert "Commits count as a reply" in box
    assert 'name="commits" value="1" checked' in text(client, "/s/o~r/replies/?commits=1")


def test_a_commit_answers_only_with_the_option(replied, client):
    """ann answered #1 only with a commit: red by default, green with commits=1."""
    default = client.get("/badge/s/o~r/replies/ann.json").json()
    counted = client.get("/badge/s/o~r/replies/ann.json?commits=1").json()
    assert (default["message"], default["status"]) == ("1/2 PRs answered", "red")
    assert (counted["message"], counted["status"]) == ("2/2 PRs answered", "green")
    assert counted["page"].endswith("/s/o~r/replies/ann/?commits=1")


def test_links_and_badges_carry_the_option(replied, client):
    """The links of the page keep commits=1; the badge of a person counts the same."""
    page = text(client, "/s/o~r/replies/?commits=1")
    assert re.search(r'href="/s/o~r/people/ann/\?commits=1"', page)
    badge = text(client, "/s/o~r/replies/ann/badge/?commits=1")
    assert "/badge/s/o~r/replies/ann.svg?commits=1" in badge
    both = text(client, "/s/o~r/replies/ann/badge/?drafts=1&commits=1")
    assert "/badge/s/o~r/replies/ann.svg?drafts=1&amp;commits=1" in both


def test_the_notice_of_unread_commits_needs_the_option(replied, client):
    """Without commits counting, commits not read yet do not matter."""
    notice = "pull request was read before commits were read"
    assert notice not in text(client, "/s/o~r/replies/")
    assert notice in text(client, "/s/o~r/replies/?commits=1")
