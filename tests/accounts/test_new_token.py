"""The page GitHub access links to the form of GitHub for a token, filled in."""

import html
import re
from datetime import date
from urllib.parse import parse_qs, urlsplit

import pytest

from community_insights.tokens.new import MONTH, YEAR, new_token_url

pytestmark = pytest.mark.django_db
DAY = date(2026, 10, 29)


def parameters(address: str) -> dict[str, str]:
    """The parameters of an address, one value each.

    Args:
        address: The address.

    Returns:
        The names and their values.
    """
    return {name: values[0] for name, values in parse_qs(urlsplit(address).query).items()}


def test_a_token_for_public_repositories_needs_no_permission():
    """The form has a name, a description and the days, and no permission."""
    address = new_token_url(MONTH, "insight.pycal.org", DAY)
    assert address.startswith("https://github.com/settings/personal-access-tokens/new?")
    assert parameters(address) == {
        "name": "Community Insights 2026-10-29",
        "description": "Reads pull requests and issues for insight.pycal.org",
        "expires_in": "30",
    }


def test_a_token_for_private_repositories_reads_them():
    """Private repositories need read access to pull requests, issues and metadata."""
    found = parameters(new_token_url(YEAR, "example.org", DAY, private=True))
    assert found["expires_in"] == "365"
    assert {found[p] for p in ("pull_requests", "issues", "metadata")} == {"read"}


def test_the_days_and_the_name_fit_into_the_limits_of_github():
    """GitHub allows 1 to 366 days and names of up to 40 characters."""
    assert 1 <= MONTH < YEAR <= 366
    assert len(parameters(new_token_url(YEAR, "x", DAY))["name"]) <= 40


def test_the_page_offers_a_token_for_a_month_and_a_year(signed_in, settings):
    """Two buttons open the form of GitHub, for this site, in a new tab."""
    settings.PRIVATE_REPOSITORIES = False
    page = signed_in.get("/dashboard/github/").content.decode()
    links = {
        text: html.unescape(href)
        for href, text in re.findall(
            r'<a class="btn btn-sm btn-outline-primary" href="(https://github\.com/settings/'
            r'personal-access-tokens/new\?[^"]+)" target="_blank" rel="noopener">([^<]+)</a>',
            page,
        )
    }
    assert set(links) == {"Token for a month", "Token for a year"}
    assert parameters(links["Token for a month"])["expires_in"] == "30"
    assert parameters(links["Token for a year"])["expires_in"] == "365"
    assert "testserver" in parameters(links["Token for a year"])["description"]
    assert "pull_requests" not in links["Token for a year"]


def test_the_page_asks_for_permissions_when_private_repositories_are_read(signed_in, settings):
    """With PRIVATE_REPOSITORIES, the tokens of the buttons read them."""
    settings.PRIVATE_REPOSITORIES = True
    page = html.unescape(signed_in.get("/dashboard/github/").content.decode())
    assert "expires_in=30&pull_requests=read&issues=read&metadata=read" in page
