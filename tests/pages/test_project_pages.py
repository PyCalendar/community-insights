"""The pages of a project and of a person: one list, offered by every menu."""

import re

import pytest

from community_insights.models import Project
from community_insights.views.project_pages import (
    PERSON_PAGES,
    PROJECT_PAGES,
    person_pages,
    project_pages,
)

pytestmark = pytest.mark.django_db


def addresses(page: str) -> set[str]:
    """The addresses of the links of a page.

    Args:
        page: The HTML.

    Returns:
        Their addresses.
    """
    return set(re.findall(r'href="([^"]+)"', page))


def test_the_pages_of_a_project_are_one_list():
    """Overview, response times, contributors, pull requests and issues, replies, badges."""
    names = [name for name, _ in PROJECT_PAGES]
    assert names[:6] == [
        "overview",
        "response_times",
        "contributors",
        "items",
        "replies",
        "badges",
    ]
    assert [n for n, _, _ in project_pages("o~r", "?last=30", several=False)] == names[:6]
    assert project_pages("o~r", "?last=30")[1][2] == "/s/o~r/response-times/?last=30"
    assert [n for n, _, _ in person_pages("o~r", "bob")] == [n for n, _ in PERSON_PAGES]


def test_the_navigation_and_the_dashboard_offer_the_same_pages(synced, signed_in):
    """The drop-down of a statistics page and the menu of the card of the dashboard."""
    pk = Project.objects.get().pk
    wanted = {address for _, _, address in project_pages(str(pk), several=False)}
    overview = signed_in.get(f"/s/{pk}/").content.decode()
    assert wanted <= addresses(overview)
    assert wanted <= addresses(signed_in.get("/dashboard/").content.decode())
    assert f'aria-current="page" href="/s/{pk}/">Overview</a>' in overview


def test_explore_offers_the_pages_of_a_public_repository(synced, client):
    """The menu of a card of Explore has every page of the repository."""
    wanted = {address for _, _, address in project_pages("o~r", several=False)}
    assert wanted <= addresses(client.get("/explore/").content.decode())


@pytest.mark.parametrize("name", ["overview", "response_times", "badges"])
def test_each_page_shows_itself_as_chosen(synced, signed_in, name):
    """The button of the drop-down names the page shown."""
    pk = Project.objects.get().pk
    title, address = next((str(t), a) for n, t, a in project_pages(str(pk)) if n == name)
    page = signed_in.get(address).content.decode()
    assert f'aria-current="page" href="{address}">{title}</a>' in page


def test_the_overview_shows_the_contributors(synced, signed_in):
    """How many contributed, by class, the most active; no charts of response times."""
    pk = Project.objects.get().pk
    page = signed_in.get(f"/s/{pk}/").content.decode()
    assert "people who contributed" in page and "Most active" in page
    assert f'href="/s/{pk}/people/bob/">bob</a>' in page
    assert "chart/responses-pr" not in page, "the response times have their own page"
    assert 'data-badge="label"' not in page, "the badges have their own page"


def test_the_pages_of_a_person_are_offered_on_each_of_them(synced, signed_in):
    """Contributions, replies, pull requests and issues, and badges of bob."""
    pk = Project.objects.get().pk
    wanted = {address for _, _, address in person_pages(str(pk), "bob")}
    for address in wanted:
        response = signed_in.get(address)
        assert response.status_code == 200, address
        assert wanted <= addresses(response.content.decode()), address


class FakeScope:
    """A scope with the given contributors."""

    def __init__(self, people):
        """Keep the contributors.

        Args:
            people: The contributors.
        """
        self.people = people

    def contributors(self):
        """The contributors.

        Returns:
            Them.
        """
        return self.people


def test_bots_are_not_among_the_most_active():
    """A bot by class or by handle is counted, but not listed as most active."""
    from community_insights.stats.contributor import Contributor
    from community_insights.views.statistics import contributor_numbers

    people = [
        Contributor("coveralls", comments=90, klass="bot"),
        Contributor("dependabot[bot]", prs_opened=80, klass="external"),
        Contributor("kim", comments=3, klass="external"),
    ]
    numbers = contributor_numbers(FakeScope(people), [])
    assert numbers["total"] == 3, "the bots still count as contributors"
    assert [p.login for p in numbers["most_active"]] == ["kim"]
