"""make check-live: the walk through a live site, here against the site of the tests."""

import httpx
import pytest

from community_insights import version
from scripts import check_live
from scripts.check_live import LiveCheck

pytestmark = pytest.mark.django_db

SIGN_IN_PAGE = "/accounts/login/"


def django_transport(client, answers=None):
    """Answer the requests of the check with the Django test client.

    Args:
        client: The test client of Django.
        answers: Answers to give instead, by path, such as a 502 while the site starts.

    Returns:
        The transport for httpx.
    """

    def handle(request: httpx.Request) -> httpx.Response:
        """Answer with the test client, or with the answers given."""
        path = request.url.raw_path.decode()
        waiting = (answers or {}).get(request.url.path)
        if waiting:
            return waiting.pop(0) if len(waiting) > 1 else waiting[0]
        answer = client.get(path)
        body = b"".join(answer.streaming_content) if answer.streaming else answer.content
        return httpx.Response(answer.status_code, headers=dict(answer.items()), content=body)

    return httpx.MockTransport(handle)


def check(client, answers=None, commit="", wait=0.0) -> LiveCheck:
    """The check of the site of the tests.

    Args:
        client: The test client of Django.
        answers: Answers to give instead, by path.
        commit: The commit the site must run.
        wait: How long to wait for it.

    Returns:
        The check.
    """
    transport = httpx.Client(transport=django_transport(client, answers))
    return LiveCheck("http://testserver", client=transport, wait=wait, commit=commit)


@pytest.fixture(autouse=True)
def no_pause(monkeypatch):
    """The waits of the check take no time."""
    monkeypatch.setattr(check_live.time, "sleep", lambda seconds: None)


def test_the_site_of_the_tests_passes(world, client, capsys):
    """Every public page, the pages of a public repository, robots.txt and the errors."""
    live = check(client)
    assert live.run() == 0, live.failures
    assert "scope /s/o~r/" in capsys.readouterr().out
    for page in ("/", "/explore/", "/about/", "/robots.txt", SIGN_IN_PAGE):
        assert live.checked[page] == 200, page
    for page in ("/s/o~r/", "/s/o~r/trends/?last=30", "/s/o~r/chart/trend-pr.svg?last=30"):
        assert live.checked[page] == 200, page
    assert live.checked["/badge/s/o~r.svg"] == 200


def test_it_waits_while_the_site_starts(world, client):
    """502 of nginx while gunicorn starts: the check waits and goes on."""
    answers = {"/health/": [httpx.Response(502), httpx.Response(502)]}
    starting = check(client, answers, wait=60)
    answers["/health/"].append(httpx.Response(200, text="ok"))
    assert starting.wait_until_up(pause=0)


def test_it_waits_for_the_commit_pushed(world, client, capsys):
    """The old container answers until the new one runs: the check waits for the commit."""
    live = check(client, commit="0" * 40, wait=0)
    assert not live.wait_until_up(pause=0)
    assert "does not name the commit 000000000000" in live.failures[0]
    running = version.get().get("commit", "")
    if running:  # a checkout with git: the about page names its commit
        assert check(client, commit=running).wait_until_up(pause=0)


def test_a_site_that_does_not_start(world, client):
    """No answer within the time is a failure."""
    live = check(client, {"/health/": [httpx.Response(503)]})
    assert live.run() == 1
    assert "not up in 0 s" in live.failures[0]


def test_failures_are_reported(world, client):
    """A page that breaks, a page that asks to sign in, robots.txt that allows everything."""
    live = check(
        client,
        {
            "/s/o~r/trends/": [httpx.Response(500, text="Server Error")],
            "/about/": [httpx.Response(302, headers={"location": SIGN_IN_PAGE})],
            "/robots.txt": [httpx.Response(200, text="User-agent: *\nAllow: /\n")],
        },
    )
    assert live.run() == 1
    text = "\n".join(live.failures)
    assert "500 /s/o~r/trends/?last=30" in text
    assert "/about/  (public, but asks to sign in)" in text
    assert "expected Disallow: /s/" in text


def test_explore_without_a_public_repository(user, client):
    """Without a public repository there are no statistics to open."""
    live = check(client)
    live.check_scope(client.get("/explore/").content.decode())
    assert "no public repository to open" in live.failures[0]


def test_a_missing_page_of_nginx_is_not_the_page_of_the_site(world, client):
    """The error pages must be those of the site, not of the proxy in front of it."""
    live = check(client, {"/s/1/": [httpx.Response(404, text="<center>nginx</center>")]})
    live.expect("/s/1/", 302)
    live.expect("/no-such-page/", 404)
    assert live.failures == ["FAIL 404 /s/1/  (expected 302)"]
