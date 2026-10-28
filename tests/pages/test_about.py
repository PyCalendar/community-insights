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
    found = licenses.reused()
    assert {p.license for p in found} == {"MIT", "BSD-2-Clause", "0BSD"}, "not the project"
    icalendar = next(p for p in found if p.license == "BSD-2-Clause")
    assert "test_with_doctest.py" in icalendar.name
    assert "Plone Foundation" in icalendar.version
    urls = {p.url.rsplit("/tree/main/", 1)[1] for p in found if p.license != "BSD-2-Clause"}
    assert urls == {
        "static/vendor/bootstrap",
        "static/vendor/chartjs",
        "static/vendor/sortable",
        "static/vendor/htmx",
    }
    root = Path(licenses.__file__).parent.parent
    for entry in found:
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


def test_the_versions_of_vendor_json_are_those_of_package_json():
    """make vendor copies the npm packages of package.json: vendor.json names their versions."""
    root = Path(licenses.__file__).parent.parent
    wanted = json.loads((root / "package.json").read_text())["dependencies"]
    for entry in json.loads((root / "static" / "vendor" / "vendor.json").read_text()):
        if "npm" in entry:
            assert wanted[entry["npm"]] == entry["version"], entry["name"]
    named = {
        entry.get("npm")
        for entry in json.loads((root / "static" / "vendor" / "vendor.json").read_text())
    }
    assert set(wanted) <= named, "every npm package the pages load is listed"


def test_python_packages_are_read_by_pip_licenses():
    """Every installed package is listed, Django with its SPDX license."""
    found = {p.name: p for p in licenses.packages()}
    assert found["Django"].license == "BSD-3-Clause"
    assert found["pip-licenses"].version


def test_the_license_text_of_a_package_is_shown(client):
    """The license of a package links to its text, served as plain text."""
    django = next(p for p in licenses.packages() if p.name == "Django")
    assert django.license_url == "/about/licenses/django/"
    response = client.get(django.license_url)
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/plain")
    assert "Django Software Foundation" in response.content.decode()


def test_the_about_page_links_the_license_texts(client):
    """The table of the Python packages links to the license texts."""
    assert b'href="/about/licenses/django/"' in client.get("/about/").content


@pytest.mark.parametrize("name", ["not-installed-at-all", "DJANGO-nope"])
def test_an_unknown_package_has_no_license_page(client, name):
    """A package that is not installed is not found."""
    assert client.get(f"/about/licenses/{name}/").status_code == 404


def test_a_package_without_a_license_file_has_no_link(monkeypatch):
    """A package that ships no license file shows its license without a link."""
    monkeypatch.setattr(
        licenses,
        "installed",
        lambda: {"x": {"name": "x", "version": "1", "licensetext": "UNKNOWN"}},
    )
    licenses.packages.cache_clear()
    try:
        assert licenses.packages()[0].license_url == ""
        assert licenses.license_text("X") is None
    finally:
        licenses.packages.cache_clear()


def test_the_license_page_ignores_the_case_of_the_name(client):
    """/about/licenses/DJANGO/ is the license of Django."""
    assert client.get("/about/licenses/DJANGO/").status_code == 200
