"""Sharing: the address of a page, and a chart with its code in four formats."""

import re

import pytest
from django.template import Context, Template
from django.test import RequestFactory

from community_insights.classify import add_handle, bot_class
from community_insights.models import Project, Repository

pytestmark = pytest.mark.django_db


def test_a_chart_of_a_project_with_its_page(synced, signed_in):
    """A chart of a project with its page."""
    pk = Project.objects.get().pk
    page = signed_in.get(f"/s/{pk}/share/responses-pr/?from=/s/{pk}/").content.decode()
    assert 'data-share-image="http://testserver/s/o~r/chart/responses-pr.svg"' in page
    assert 'data-share-link="http://testserver/s/o~r/"' in page
    assert f'href="/s/{pk}/">Back to the page' in page, "back to the own page"
    assert "o/r: first response times of pull requests" in page
    for name in ("markdown", "rst", "html", "link"):
        assert f'data-share="{name}"' in page
        assert f'data-copy="#chart-{name}"' in page
    assert "public repositories of your projects" in page and "o~r" in page
    assert "only you can see it" not in page


def test_the_parameters_of_the_chart_stay_but_not_the_theme(synced, signed_in):
    """The parameters of the chart stay but not the theme."""
    pk = Project.objects.get().pk
    page = signed_in.get(
        f"/s/{pk}/share/months/?login=bob&theme=dark&from=/s/{pk}/people/bob/"
    ).content.decode()
    assert 'data-share-image="http://testserver/s/o~r/chart/months.svg?login=bob"' in page
    assert 'data-share-link="http://testserver/s/o~r/people/bob/"' in page
    assert "contributions per month (bob)" in page


@pytest.mark.parametrize(
    "page", ["//evil.example/x", "https://evil.example/", "javascript:alert(1)", ""]
)
def test_only_pages_of_this_site_are_linked(synced, signed_in, page):
    """Only pages of this site are linked."""
    pk = Project.objects.get().pk
    html = signed_in.get(f"/s/{pk}/share/hours/", {"from": page}).content.decode()
    main = html[html.index("<main") : html.index("</main>")]
    assert 'data-share-link="http://testserver/s/o~r/"' in main
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


def shared(page: str, name: str) -> str:
    """The value of a data- attribute of the page, with &amp; as &."""
    start = page.index(f'{name}="') + len(name) + 2
    return page[start : page.index('"', start)].replace("&amp;", "&")


def test_the_shared_chart_keeps_the_time_range_and_the_classes(synced, signed_in, user):
    """Others see the same numbers: the time range and the own classes are in both addresses."""
    add_handle(bot_class(user), "maint")  # the classes differ from the default ones
    pk = Project.objects.get().pk
    page = signed_in.get(
        f"/s/{pk}/share/hours/", {"last": "30", "from": f"/s/{pk}/?last=30"}
    ).content.decode()
    image, link = shared(page, "data-share-image"), shared(page, "data-share-link")
    for address in (image, link):
        assert address.startswith("http://testserver/s/o~r/"), address
        assert "last=30" in address and "classes=" in address, address


def undated(svg: bytes) -> bytes:
    """An SVG without the time it was drawn at and the random ids of matplotlib."""
    return re.sub(rb"#?[mp][0-9a-f]{10}\b", b"", re.sub(rb"<dc:date>[^<]*</dc:date>", b"", svg))


def test_visitors_open_what_is_shared(synced, signed_in, client, user):
    """The shared image and page of a project open without a sign in, with the same image."""
    add_handle(bot_class(user), "maint")
    pk = Project.objects.get().pk
    page = signed_in.get(
        f"/s/{pk}/share/responses-pr/",
        {"since": "2026-01-01", "from": f"/s/{pk}/?since=2026-01-01"},
    ).content.decode()
    image, link = shared(page, "data-share-image"), shared(page, "data-share-link")
    own = signed_in.get(f"/s/{pk}/chart/responses-pr.svg?since=2026-01-01").content
    signed_in.logout()
    seen = client.get(image.removeprefix("http://testserver"))
    assert seen.status_code == 200
    assert undated(seen.content) == undated(own), "the same chart as the owner's"
    assert client.get(link.removeprefix("http://testserver")).status_code == 200


def test_a_project_without_public_repositories_is_shared_as_it_is(synced, signed_in):
    """Without a public repository, the addresses stay those of the project, with a warning."""
    Repository.objects.update(is_private=True)
    pk = Project.objects.get().pk
    page = signed_in.get(f"/s/{pk}/share/hours/?from=/s/{pk}/").content.decode()
    assert f'data-share-link="http://testserver/s/{pk}/"' in page
    assert "only you can see it" in page


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("/s/{pk}/?last=30", "/s/o~r/?last=30"),
        ("/s/{pk}/people/bob/?since=2026-01-01", "/s/o~r/people/bob/?since=2026-01-01"),
        (
            "/s/{pk}/contributors/?where=prs_total+%3E+0&sort=-prs_total&group=&last=30",
            "/s/o~r/contributors/?where=prs_total+%3E+0&sort=-prs_total&group=&last=30",
        ),
        ("/s/o~r/items/?kind=pr", "/s/o~r/items/?kind=pr"),
    ],
)
def test_the_share_button_copies_the_address_for_everybody(
    synced, signed_in, client, url, expected
):
    """The share button of a page copies its address with the public repositories."""
    pk = Project.objects.get().pk
    page = signed_in.get(url.format(pk=pk)).content.decode()
    address = shared(page, "data-copy-url")
    assert address == f"http://testserver{expected}"
    signed_in.logout()
    assert client.get(expected).status_code == 200


def test_the_share_button_carries_the_own_classes(synced, signed_in, user):
    """With classes other than the default ones, the copied address names them."""
    add_handle(bot_class(user), "maint")
    pk = Project.objects.get().pk
    address = shared(signed_in.get(f"/s/{pk}/").content.decode(), "data-copy-url")
    assert address.startswith("http://testserver/s/o~r/?classes="), address


def test_an_address_that_is_no_page_of_a_scope_stays(synced, signed_in):
    """Scope.shared leaves other addresses as they are, without from and theme."""
    from community_insights.views.scope import Scope

    scope = Scope(Project.objects.get().user, str(Project.objects.get().pk), {"last": "7"})
    assert scope.shared("/about/?from=/x&theme=dark") == "/about/?last=7"
    assert scope.shared(f"/s/{scope.text}/?since=2026-01-01") == "/s/o~r/?since=2026-01-01"
