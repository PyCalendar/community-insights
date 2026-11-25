"""Pages of projects that are all public lead to their public address, without the numbers."""

import pytest

from community_insights.models import Project
from community_insights.public_scope import address_of, public_scope
from community_insights.sync import store_repository

from ..fakes import repo

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    """Django's client: the redirects themselves are tested here.

    Returns:
        The client.
    """
    from django.test import Client

    return Client()


@pytest.fixture
def icalendar(user):
    """The project of the public repository collective/icalendar.

    Returns:
        The project.
    """
    project = Project.objects.create(user=user, target="collective/icalendar")
    project.repositories.add(store_repository(repo("collective/icalendar", 5)))
    return project


def owner_project(user, target: str, names: list[str], private=()) -> Project:
    """A project of an organisation with repositories.

    Args:
        user: Its user.
        target: The organisation.
        names: The full names of its repositories.
        private: The names of the private ones.

    Returns:
        The project.
    """
    project = Project.objects.create(user=user, target=target, is_private=bool(private))
    for name in names:
        project.repositories.add(store_repository(repo(name, 1, private=name in private)))
    return project


def test_one_public_repository(icalendar):
    """The project of collective/icalendar is collective~icalendar."""
    assert public_scope([icalendar]) == "collective~icalendar"
    assert address_of(icalendar) == icalendar.address == "collective~icalendar"


def test_an_organisation_is_its_login(user):
    """All known public repositories of plone: "plone"; one more of somebody else: listed."""
    plone = owner_project(user, "plone", ["plone/volto", "plone/plone.api"])
    assert public_scope([plone]) == "plone"
    store_repository(repo("plone/other", 1))
    assert public_scope([plone]) == "plone~plone.api+plone~volto", "plone/other is not in it"


def test_several_projects(user, icalendar):
    """Projects together: their repositories joined with +."""
    plone = owner_project(user, "plone", ["plone/volto"])
    assert public_scope([icalendar, plone]) == "plone+collective~icalendar"


def test_a_private_repository_has_no_public_address(user):
    """With a private repository, the project keeps its number and needs a sign in."""
    secret = owner_project(user, "o", ["o/open", "o/secret"], private=["o/secret"])
    assert public_scope([secret]) is None
    assert address_of(secret) == str(secret.pk)


def test_a_project_without_repositories(user):
    """Not read yet: no public address."""
    empty = Project.objects.create(user=user, target="o/new")
    assert public_scope([empty]) is None and public_scope([]) is None


def test_a_visitor_is_led_to_the_public_page(icalendar, client):
    """https://insight.pycal.org/s/1/suggestions/ needed a sign in; now it leads to the same
    page of collective~icalendar, with the parameters."""
    response = client.get(f"/s/{icalendar.pk}/suggestions/?page=2&state=open")
    assert response.status_code == 302
    assert response["Location"] == "/s/collective~icalendar/suggestions/?page=2&state=open"


def test_the_owner_is_led_to_the_public_page_too(icalendar, signed_in):
    """The public page is preferred, also for the owner."""
    response = signed_in.get(f"/s/{icalendar.pk}/items/")
    assert response["Location"] == "/s/collective~icalendar/items/"
    combined = signed_in.get("/s/all/people/ann/")
    assert combined["Location"] == "/s/collective~icalendar/people/ann/"


def test_a_private_project_still_needs_a_sign_in(user, client):
    """Private: the sign in for visitors, the page for the owner."""
    secret = owner_project(user, "o", ["o/secret"], private=["o/secret"])
    response = client.get(f"/s/{secret.pk}/")
    assert response.status_code == 302 and "/accounts/login/" in response["Location"]
    client.force_login(user)
    assert client.get(f"/s/{secret.pk}/").status_code == 200


def test_a_project_that_does_not_exist(user, client):
    """No project 999: the sign in for visitors, not found for a user; no public page."""
    assert "/accounts/login/" in client.get("/s/999/")["Location"]
    client.force_login(user)
    assert client.get("/s/999/").status_code == 404


def test_forms_are_not_led_away(icalendar, signed_in):
    """A form sent to a project is answered there: a redirect would lose it."""
    response = signed_in.post(f"/s/{icalendar.pk}/fetch/", {"next": "/"})
    assert response.status_code != 302 or "collective~icalendar" not in response["Location"]


def test_the_dashboard_links_the_public_address(icalendar, signed_in):
    """The card of the project and its menu use collective~icalendar, not the number."""
    page = signed_in.get("/dashboard/").content.decode()
    assert 'href="/s/collective~icalendar/"' in page
    assert f'href="/s/{icalendar.pk}/' not in page
