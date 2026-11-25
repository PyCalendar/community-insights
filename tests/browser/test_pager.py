"""The pager of the lists in a real browser: the drop-down jumps to a page."""

import re
from datetime import UTC, datetime, timedelta

import pytest
from playwright.sync_api import expect

from community_insights.models import Item
from community_insights.sync import store_repository

from ..fakes import repo


@pytest.fixture
def many(site):
    """The public repository o/r with 120 issues: 3 pages of the table.

    Args:
        site: The site.

    Returns:
        The site.
    """
    repository = store_repository(repo("o/r", 5))
    start = datetime(2026, 1, 1, 9, tzinfo=UTC)
    Item.objects.bulk_create(
        Item(
            repository=repository,
            kind=Item.ISSUE,
            number=n,
            title=f"Issue {n}",
            author="ann",
            state="open",
            created_at=start + timedelta(hours=n),
            updated_at=start + timedelta(hours=n),
        )
        for n in range(1, 121)
    )
    return site


def test_the_drop_down_jumps_to_a_page(many):
    """Choosing 3 opens the third page, with the other parameters; previous goes back."""
    many.open("/s/o~r/items/?kind=issue")
    pages = many.page.locator("[data-pager-select]")
    expect(pages).to_have_value("1")
    pages.select_option("3")
    expect(many.page).to_have_url(re.compile(r"kind=issue.*page=3"))
    expect(many.page.locator("[data-pager-select]")).to_have_value("3")
    expect(many.page.locator("[data-pager-next]")).to_have_count(0)
    many.page.locator("[data-pager-previous]").click()
    expect(many.page).to_have_url(re.compile(r"page=2"))
    expect(many.page.locator("[data-pager-select]")).to_have_value("2")
