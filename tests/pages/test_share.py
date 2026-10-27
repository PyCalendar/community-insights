"""Sharing: the address of a page, and a chart with its code in four formats."""

import pytest
from django.template import Context, Template
from django.test import RequestFactory

from community_insights.models import Project

pytestmark = pytest.mark.django_db


def test_a_chart_of_a_project_with_its_page(synced, signed_in):
    """A chart of a project with its page."""
    pk = Project.objects.get().pk
    page = signed_in.get(f"/s/{pk}/share/responses-pr/?from=/s/{pk}/").content.decode()
    assert f'data-share-image="http://testserver/s/{pk}/chart/responses-pr.svg"' in page
    assert f'data-share-link="http://testserver/s/{pk}/"' in page
    assert "o/r: first response times of pull requests" in page
    for name in ("markdown", "rst", "html", "link"):
        assert f'data-share="{name}"' in page
        assert f'data-copy="#chart-{name}"' in page
    assert "only you can see it" in page, "a project is private"


def test_the_parameters_of_the_chart_stay_but_not_the_theme(synced, signed_in):
    """The parameters of the chart stay but not the theme."""
    pk = Project.objects.get().pk
    page = signed_in.get(
        f"/s/{pk}/share/months/?login=bob&theme=dark&from=/s/{pk}/people/bob/"
    ).content.decode()
    assert f'data-share-image="http://testserver/s/{pk}/chart/months.svg?login=bob"' in page
    assert f'data-share-link="http://testserver/s/{pk}/people/bob/"' in page
    assert "contributions per month (bob)" in page


@pytest.mark.parametrize(
    "page", ["//evil.example/x", "https://evil.example/", "javascript:alert(1)", ""]
)
def test_only_pages_of_this_site_are_linked(synced, signed_in, page):
    """Only pages of this site are linked."""
    pk = Project.objects.get().pk
    html = signed_in.get(f"/s/{pk}/share/hours/", {"from": page}).content.decode()
    main = html[html.index("<main") : html.index("</main>")]
    assert f'data-share-link="http://testserver/s/{pk}/"' in main
    assert "evil" not in main and "javascript:" not in main


def test_a_public_chart_for_everybody(synced, client):
    """A public chart for everybody."""
    page = client.get("/s/o~r/share/responses-issue/?from=/s/o~r/").content.decode()
    assert 'data-share-image="http://testserver/s/o~r/chart/responses-issue.svg"' in page
    assert "only you can see it" not in page


def test_unknown_charts_and_projects_of_others(synced, signed_in, client):
    """Unknown charts and projects of others."""
    pk = Project.objects.get().pk
    assert signed_in.get(f"/s/{pk}/share/nothing/").status_code == 404
    signed_in.logout()
    assert client.get(f"/s/{pk}/share/hours/").status_code == 302, "to the sign in"


def test_the_charts_link_to_their_share_page(synced, signed_in):
    """The charts link to their share page."""
    pk = Project.objects.get().pk
    page = signed_in.get(f"/s/{pk}/?since=2026-01-01").content.decode()
    assert "Share this chart" in page
    assert (
        f"/s/{pk}/share/responses-pr/?since=2026-01-01&amp;from=%2Fs%2F{pk}%2F%3Fsince%3D2026-01-01"
        in page
    )


@pytest.mark.parametrize("url", ["/s/{pk}/", "/s/{pk}/contributors/", "/s/{pk}/people/bob/"])
def test_statistics_pages_have_a_share_button(synced, signed_in, url):
    """Statistics pages have a share button."""
    pk = Project.objects.get().pk
    page = signed_in.get(url.format(pk=pk)).content.decode()
    assert "data-copy-url" in page
    assert "js/copy.js" in page


def test_the_share_address_of_something_that_is_no_chart():
    """The share address of something that is no chart."""
    template = Template("{% load community %}{% chart_share_url src %}")
    request = RequestFactory().get("/")
    for src in ["/badge/x.svg", "/nowhere/at/all/", "https://example.org/x.svg"]:
        assert template.render(Context({"src": src, "request": request})) == "", src


def test_the_share_address_without_a_request():
    """The share address without a request."""
    template = Template("{% load community %}{% chart_share_url src %}")
    assert template.render(Context({"src": "/s/o~r/chart/hours.svg?login=bob"})) == (
        "/s/o~r/share/hours/?login=bob"
    )
