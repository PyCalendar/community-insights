"""The About page: version, where its code is, and the licenses."""

import json

import pytest
from django.contrib.staticfiles import finders

from community_insights import licenses, version

pytestmark = pytest.mark.django_db


def test_the_scripts_of_the_pages_and_their_licenses(client):
    page = client.get("/about/").content.decode()
    for name in (
        "Bootstrap",
        "Django JavaScript catalog",
        "Contributor Community Insights scripts",
    ):
        assert name in page
    assert "/static/vendor/bootstrap/LICENSE.txt" in page
    assert "Python packages on the server" in page and "Django" in page


def test_every_file_of_vendor_json_is_served():
    for entry in json.loads(licenses.VENDOR.read_text()):
        for path in entry["files"]:
            assert finders.find(path), path
        if not entry["license_url"].startswith(("http", "LICENSE")):
            assert finders.find(entry["license_url"]), entry["license_url"]


def test_every_script_of_the_site_is_listed():
    from pathlib import Path

    listed = {p for e in json.loads(licenses.VENDOR.read_text()) for p in e["files"]}
    own = Path(licenses.VENDOR).parent.parent / "js"
    assert {f"js/{p.name}" for p in own.glob("*.js")} <= listed


def test_code_of_a_release_and_of_a_commit():
    release = version.source_links("https://example.org/r", {"tag": "v1.2.3", "commit_full": "abc"})
    assert release["this_version_url"] == "https://example.org/r/tree/v1.2.3"
    commit = version.source_links("https://example.org/r/", {"commit_full": "abc123"})
    assert commit == {
        "commit_url": "https://example.org/r/commit/abc123",
        "this_version_url": "https://example.org/r/tree/abc123",
    }
    nothing = version.source_links("https://example.org/r", {})
    assert nothing["this_version_url"] == "https://example.org/r"


def test_the_repository_is_a_setting(client, settings):
    settings.SOURCE_URL = "https://example.org/fork"
    page = client.get("/about/").content.decode()
    assert 'href="https://example.org/fork"' in page or "https://example.org/fork/tree/" in page
    assert "https://example.org/fork/issues/new" in page
    assert "github.com/PyCalendar/community-insights" not in page


def test_a_checkout_knows_its_commit():
    info = version.get()
    if not version.VERSION_FILE.exists():
        assert info["commit_full"] == version.git_commit()
