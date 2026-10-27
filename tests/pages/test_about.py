"""The About page: version, where its code is, and the licenses."""

import json
from pathlib import Path

import pytest
from django.contrib.staticfiles import finders

from community_insights import licenses, version

pytestmark = pytest.mark.django_db


def test_the_scripts_of_the_pages_and_their_licenses(client):
    """The scripts of the pages and their licenses."""
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
    """Every file of vendor json is served."""
    for entry in json.loads(licenses.VENDOR.read_text()):
        for path in entry["files"]:
            assert finders.find(path), path
        if not entry["license_url"].startswith(("http", "LICENSE")):
            assert finders.find(entry["license_url"]), entry["license_url"]


def test_every_script_of_the_site_is_listed():
    """Every script of the site is listed."""
    from pathlib import Path

    listed = {p for e in json.loads(licenses.VENDOR.read_text()) for p in e["files"]}
    own = Path(licenses.VENDOR).parent.parent / "js"
    assert {f"js/{p.name}" for p in own.glob("*.js")} <= listed


def test_code_of_a_release_and_of_a_commit():
    """Code of a release and of a commit."""
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
    """The repository is a setting."""
    settings.SOURCE_URL = "https://example.org/fork"
    page = client.get("/about/").content.decode()
    assert 'href="https://example.org/fork"' in page or "https://example.org/fork/tree/" in page
    assert "https://example.org/fork/issues/new" in page
    assert "github.com/PyCalendar/community-insights" not in page


def test_a_checkout_knows_its_commit():
    """A checkout knows its commit."""
    info = version.get()
    if not version.VERSION_FILE.exists():
        assert info["commit_full"] == version.git_commit()


def test_reused_code_is_read_from_reuse_toml():
    """Reused code is read from reuse toml."""
    entries = {p.license: p for p in licenses.reused()}
    assert set(entries) == {"MIT", "BSD-2-Clause"}, "not the project itself"
    assert "test_with_doctest.py" in entries["BSD-2-Clause"].name
    assert "Plone Foundation" in entries["BSD-2-Clause"].version
    assert entries["MIT"].url.endswith("/tree/main/static/vendor/bootstrap")
    root = Path(licenses.__file__).parent.parent
    for entry in entries.values():
        assert entry.license_url.endswith(f"/blob/main/LICENSES/{entry.license}.txt")
        assert (root / "LICENSES" / f"{entry.license}.txt").is_file()


def test_reused_reads_single_values_and_needs_no_file(tmp_path):
    """Reused reads single values and needs no file."""
    assert licenses.reused(tmp_path / "missing.toml") == []
    path = tmp_path / "REUSE.toml"
    path.write_text(
        'version = 1\n[[annotations]]\npath = "a/**"\n'
        'SPDX-FileCopyrightText = "2020 Kim"\nSPDX-License-Identifier = "MIT"\n'
    )
    (entry,) = licenses.reused(path)
    assert (entry.name, entry.version, entry.license) == ("a/**", "2020 Kim", "MIT")
    assert entry.url.endswith("/tree/main/a")


@pytest.mark.django_db
def test_the_about_page_shows_the_reused_code(client):
    """The about page shows the reused code."""
    html = client.get("/about/").content.decode()
    assert "Code from other projects" in html
    assert "BSD-2-Clause" in html
