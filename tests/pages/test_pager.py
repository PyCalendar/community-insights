"""One pager for every list of the site: previous, a drop-down to jump to a page, next."""

import re

import pytest

from community_insights.sync import store_repository
from community_insights.views import explore

from ..data import read_repository
from ..fakes import FakeClient, item, repo

pytestmark = pytest.mark.django_db


def pager(page: str) -> str:
    """The pager of a page.

    Args:
        page: The HTML.

    Returns:
        The HTML of the pager.
    """
    found = re.search(r"<nav[^>]*data-pager.*?</nav>", page, re.S)
    assert found, "the page has the pager"
    return found.group(0)


def options(html: str) -> list[tuple[str, bool]]:
    """The pages of the drop-down and whether each is chosen.

    Args:
        html: The HTML of the pager.

    Returns:
        The number and whether it is selected, for each option.
    """
    return [
        (number, bool(chosen))
        for number, chosen in re.findall(r'<option value="(\d+)"( selected)?>', html)
    ]


@pytest.fixture
def many_items(user):
    """The public repository o/r with 120 issues: 3 pages of the table of 50.

    Returns:
        The repository.
    """
    repository = store_repository(repo("o/r", 5))
    issues = [item(n, "ann", f"2026-01-{1 + n % 28:02d}T09:00:00Z") for n in range(1, 121)]
    read_repository(FakeClient(issues=issues), repository)
    return repository


def test_the_tables_have_the_pager(many_items, client):
    """The table of pull requests and issues: page 2 of 3 with the other parameters."""
    page = client.get("/s/o~r/items/?kind=issue&page=2").content.decode()
    html = pager(page)
    assert options(html) == [("1", False), ("2", True), ("3", False)]
    assert "of 3" in html
    assert re.search(r'href="\?kind=issue&amp;page=1"[^>]*data-pager-previous', html)
    assert re.search(r'href="\?kind=issue&amp;page=3"[^>]*data-pager-next', html)
    assert '<input type="hidden" name="kind" value="issue">' in html, "the drop-down keeps it"
    assert 'name="page" data-submit-on-change' in html
    assert 'class="pagination' not in page, "not the pager of django-tables2"


def test_the_first_and_the_last_page(many_items, client):
    """No previous on the first page, no next on the last."""
    first = pager(client.get("/s/o~r/items/").content.decode())
    assert "data-pager-previous" not in first and "data-pager-next" in first
    last = pager(client.get("/s/o~r/items/?page=3").content.decode())
    assert "data-pager-next" not in last and "data-pager-previous" in last


def test_one_page_has_no_pager(user, client):
    """A list that fits on one page has no pager."""
    repository = store_repository(repo("o/r", 5))
    read_repository(FakeClient(issues=[item(1, "ann", "2026-01-01T09:00:00Z")]), repository)
    assert "data-pager" not in client.get("/s/o~r/items/").content.decode()


def test_explore_has_the_same_pager(many_items, client, monkeypatch):
    """The repositories of Explore, with the search kept."""
    for number in range(3):
        store_repository(repo(f"o/r{number}", 1))
    monkeypatch.setattr(explore, "PAGE", 2)
    html = pager(client.get("/explore/?q=o%2Fr").content.decode())
    assert options(html) == [("1", True), ("2", False)]
    assert '<input type="hidden" name="q" value="o/r">' in html
    assert 'href="?q=o%2Fr&amp;page=2"' in html
