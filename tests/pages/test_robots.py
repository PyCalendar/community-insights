"""robots.txt: crawlers read the start page, Explore, About and the badges, not the pages for
people, which are computed on each request and link to hundreds of people each."""

from pathlib import Path
from urllib.robotparser import RobotFileParser

import pytest

ROOT = Path(__file__).parents[2]
SITE = "https://insight.example.org"

ALLOWED = [
    "/",
    "/explore/",
    "/about/",
    "/badge/s/o~r.svg",
    "/badge/s/o~r/replies/bob.png",
]
FOR_PEOPLE = [
    "/s/o~r/",
    "/s/o~r/contributors/",
    "/s/o~r/people/bob/",
    "/s/o~r/people/bob/items/?kind=pr",
    "/s/o~r/replies/",
    "/s/o~r/data/responses.ods",
    "/s/o~r/fetch/?next=/s/o~r/",
    "/accounts/login/",
    "/dashboard/",
    "/admin/",
    "/explore/submit/",
    "/i18n/setlang/",
]


@pytest.fixture
def robots(client) -> RobotFileParser:
    """The rules the site serves, read as a crawler reads them.

    Returns:
        The parsed rules.
    """
    response = client.get("/robots.txt")
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/plain")
    parser = RobotFileParser()
    parser.parse(response.content.decode().splitlines())
    return parser


@pytest.mark.parametrize("path", ALLOWED)
def test_crawlers_may_read_the_public_entry_pages_and_badges(robots, path):
    """The start page, Explore, About and the badges may be crawled."""
    assert robots.can_fetch("Googlebot", SITE + path)


@pytest.mark.parametrize("path", FOR_PEOPLE)
def test_crawlers_do_not_read_the_pages_for_people(robots, path):
    """The statistics, accounts and forms are not crawled."""
    assert not robots.can_fetch("Googlebot", SITE + path)


def test_every_disallowed_prefix_is_an_address_of_the_site():
    """A rule for an address the site does not have would protect nothing: a typo."""
    from django.urls import get_resolver

    patterns = {str(p.pattern) for p in get_resolver().url_patterns}
    rules = (ROOT / "static" / "robots.txt").read_text().splitlines()
    for line in rules:
        if line.startswith("Disallow:"):
            prefix = line.split(":", 1)[1].strip().lstrip("/")
            assert any(p.startswith(prefix) or prefix.startswith(p) for p in patterns if p), line


def test_nginx_serves_robots_txt_without_the_site():
    """In the container, nginx answers robots.txt from the collected static files."""
    config = (ROOT / "docker" / "nginx.conf").read_text()
    assert "location = /robots.txt" in config
    assert "alias /app/staticfiles/robots.txt;" in config
