"""The pages show the data of the database and never ask GitHub."""

import json

import pytest

from community_insights.models import (
    Project,
)

pytestmark = pytest.mark.django_db


def test_pages_render(synced, signed_in):
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
        "/dashboard/cache/",
    ]:
        response = signed_in.get(url)
        assert response.status_code == 200, url
    assert b"Asia/Tokyo" in signed_in.get(f"/s/{scope}/people/bob/").content


def test_charts_are_svg(synced, signed_in):
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
    pk = world["empty"].pk
    for url in [f"/s/{pk}/", f"/s/{pk}/contributors/", f"/s/{pk}/chart/responses-pr.svg"]:
        assert signed_in.get(url).status_code == 200, url
    assert signed_in.get(f"/s/{pk}/people/bob/").status_code == 404
    assert signed_in.get(f"/s/{pk}/data/items.csv").content == b""
    data = json.loads(signed_in.get(f"/s/{pk}/data/responses.json").content)
    assert data["rows"] == [] and data["repositories"] == ["o/empty"]


def test_dashboard_card_says_when_the_data_is_complete(world, signed_in):  # noqa: F811
    page = signed_in.get("/dashboard/").content.decode()
    assert "complete in about" in page, "the fixture has a running job"
