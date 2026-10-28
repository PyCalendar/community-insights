"""Browser tests with Firefox and Playwright (``make test-browser``).

    make test-browser                          # headless Firefox, 1280x900
    make test-browser WINDOW=375x812           # the size of a phone
    make test-browser BROWSER_FLAGS=--headed       # watch it
    TIME_ZONE=America/New_York make test-browser

GitHub is never used: the client of the views is replaced by a fake in this process, which
also runs the live server.
"""

import os
from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.fakes import FakeClient

from .site import Site

# Playwright's sync API runs an event loop; the database is used from the test itself
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")
TIME_ZONE = os.environ.get("TIME_ZONE", "Asia/Tokyo")
WINDOW = os.environ.get("WINDOW") or "1280x900"
HERE = Path(__file__).parent
# milliseconds; the runners of GitHub can be much slower than a computer of a developer
TIMEOUT = 30_000
NAVIGATION_TIMEOUT = 60_000  # the first page also starts Django's templates and static files
expect.set_options(timeout=TIMEOUT)


def pytest_collection_modifyitems(items):
    """The tests of this folder are browser tests: ``-m browser`` runs them.

    Args:
        items: The collected tests.
    """
    for test in items:
        if HERE in Path(test.path).parents:
            test.add_marker(pytest.mark.browser)


@pytest.fixture
def browser_context_args(browser_context_args):
    """The browser in the time zone and window size asked for, in English.

    Args:
        browser_context_args: The arguments of pytest-playwright.

    Returns:
        The arguments with the time zone, the size of the window and the language.
    """
    width, height = (int(number) for number in WINDOW.split("x"))
    return {
        **browser_context_args,
        "timezone_id": TIME_ZONE,
        "viewport": {"width": width, "height": height},
        "locale": "en-US",
    }


@pytest.fixture
def fake(monkeypatch):
    """A fake GitHub for the views of the live server.

    Args:
        monkeypatch: Replaces the client of GitHub.

    Returns:
        The fake.
    """
    found = FakeClient()
    monkeypatch.setattr("community_insights.github.Client", lambda token: found)
    return found


@pytest.fixture
def site(page, live_server, fake):
    """The site in Firefox.

    Args:
        page: The page of Playwright.
        live_server: The site, served by pytest-django.
        fake: The fake GitHub.

    Returns:
        The site to use in the page.
    """
    page.set_default_timeout(TIMEOUT)
    page.set_default_navigation_timeout(NAVIGATION_TIMEOUT)
    return Site(page, live_server.url, fake, TIME_ZONE)


@pytest.fixture
def alice(site):
    """Alice signed up.

    Args:
        site: The site.

    Returns:
        The site, signed in as alice@example.org.
    """
    site.sign_up("alice@example.org")
    return site


@pytest.fixture
def project(alice):
    """Alice has a token and the project o/r with pull requests and issues on GitHub.

    Args:
        alice: The site, signed in.

    Returns:
        The site.
    """
    alice.add_token()
    alice.github_has("o/r", 3)
    alice.repository_has_items()
    return alice


@pytest.fixture
def read(project):
    """The project o/r was added and read from GitHub.

    Args:
        project: The site, with the project on GitHub.

    Returns:
        The site.
    """
    project.add_project("o/r")
    project.read_project("o/r")
    return project
