"""The pages show the data of the database and never ask GitHub."""

import json

import pytest

from community_insights.models import (
    Project,
)

pytestmark = pytest.mark.django_db


def test_pages_render(synced, signed_in):
    """Pages render."""
    project = Project.objects.get()
    scope = str(project.pk)
    for url in [
        "/dashboard/",
        f"/s/{scope}/",
        "/s/all/",
        f"/s/{scope}/contributors/",
        f"/s/{scope}/contributors/?q=bob&sort=response&class=external",
        f"/s/{scope}/people/bob/",
        "/dashboard/classes/",
    ]:
        response = signed_in.get(url)
        assert response.status_code == 200, url
    assert b"Asia/Tokyo" in signed_in.get(f"/s/{scope}/people/bob/").content


def test_charts_are_svg(synced, signed_in):
    """Charts are svg."""
    scope = str(Project.objects.get().pk)
    for name, query in [
        ("responses-pr", ""),
        ("responses-issue", ""),
        ("hours", "?login=bob"),
        ("heatmap", "?login=bob"),
        ("months", "?login=bob"),
    ]:
        response = signed_in.get(f"/s/{scope}/chart/{name}.svg{query}")
        assert response.status_code == 200 and response["Content-Type"] == "image/svg+xml", name
        assert b"<svg" in response.content


def test_viewing_never_uses_github(synced, signed_in, monkeypatch):
    """Statistics, charts and badges come from the database; only a sync reads GitHub."""

    def refuse(*args, **kwargs):
        """Fail: the pages must not use GitHub."""
        raise AssertionError("GitHub was used")

    monkeypatch.setattr("community_insights.github.Client", refuse)
    scope = str(Project.objects.get().pk)
    token = Project.objects.get().badge_token
    for url in [
        f"/s/{scope}/",
        f"/s/{scope}/contributors/",
        f"/s/{scope}/people/bob/",
        f"/s/{scope}/chart/responses-pr.svg",
        f"/s/{scope}/chart/heatmap.svg?login=bob",
        f"/badge/{token}.svg",
    ]:
        assert signed_in.get(url).status_code == 200, url


def test_empty_project_pages(world, signed_in):  # noqa: F811
    """Empty project pages."""
    pk = world["empty"].pk
    for url in [f"/s/{pk}/", f"/s/{pk}/contributors/", f"/s/{pk}/chart/responses-pr.svg"]:
        assert signed_in.get(url).status_code == 200, url
    assert signed_in.get(f"/s/{pk}/people/bob/").status_code == 404
    assert signed_in.get(f"/s/{pk}/data/items.csv").content == b""
    data = json.loads(signed_in.get(f"/s/{pk}/data/responses.json").content)
    assert data["rows"] == [] and data["repositories"] == ["o/empty"]


def test_dashboard_card_says_when_the_data_is_complete(world, signed_in):  # noqa: F811
    """Dashboard card says when the data is complete."""
    page = signed_in.get("/dashboard/").content.decode()
    assert "complete in about" in page, "the fixture has a running job"


@pytest.mark.parametrize("url", ["/s/{pk}/", "/s/{pk}/contributors/", "/s/{pk}/items/"])
def test_the_time_range_is_below_the_data_from_github(synced, signed_in, url):
    """From, To and the last days come after the data and its link Read from GitHub."""
    pk = Project.objects.get().pk
    page = signed_in.get(url.format(pk=pk)).content.decode()
    assert 'class="data-panel' in page
    assert page.index('class="data-panel') < page.index(
        'class="row g-2 align-items-end mb-3 date-range"'
    )
