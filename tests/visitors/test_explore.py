"""People without an account: Explore, the public statistics, submitting."""

import pytest

from community_insights.models import FetchJob, Project, Repository
from community_insights.sync import store_repository

from ..fakes import FakeClient, item, repo

pytestmark = pytest.mark.django_db


def test_the_start_page_is_explore_with_the_public_repositories(world, client):
    """The start page is explore with the public repositories."""
    page = client.get("/").content.decode()
    assert "Add owner/name or an organisation" in page
    assert "o/r" in page and 'href="/s/o~r/"' in page
    assert "Sign up with email" in page


def test_private_repositories_are_not_shown(world, client):
    """Private repositories are not shown."""
    store_repository({**repo("o/secret"), "isPrivate": True})
    assert "o/secret" not in client.get("/explore/").content.decode()
    assert client.get("/s/o~secret/").status_code == 404


def test_search(world, client):
    """Search."""
    page = client.get("/explore/?q=empty").content.decode()
    assert "o/empty" in page and 'href="/s/o~r/"' not in page


@pytest.mark.parametrize(
    "url",
    [
        "/s/o~r/",
        "/s/o/",
        "/s/o~r+o~empty/",
        "/s/o~r/contributors/",
        "/s/o~r/contributors/?where=prs_total+%3E+0&group=user_class",
        "/s/o~r/items/",
        "/s/o~r/compare/",
        "/s/o~r/people/bob/",
        "/s/o~r/chart/responses-pr.svg",
        "/s/o~r/chart/heatmap.svg?login=bob",
        "/s/o~r/data/responses.csv",
        "/s/o~r/data/contributors.ods",
        "/s/o~r/contributors.ods",
        "/s/o~r/progress.json",
        "/badge/s/o~r.svg?kind=pr&percentile=90",
    ],
)
def test_public_statistics_for_everybody(world, client, url):
    """Public statistics for everybody."""
    assert client.get(url, follow=True).status_code == 200, url


@pytest.mark.parametrize("scope", ["nothing~here", "bad name", "a~b~c", "o~"])
def test_unknown_public_scopes(world, client, scope):
    """Unknown public scopes."""
    assert client.get(f"/s/{scope}/").status_code == 404


def test_projects_need_a_sign_in(world, client):
    """Projects need a sign in."""
    response = client.get(f"/s/{world['project'].pk}/")
    assert response.status_code == 302 and response["Location"].startswith("/accounts/login/")
    assert client.get("/badge/s/1.svg").status_code == 404, "projects have secret badges"


def test_visitors_cannot_save_queries(world, client):
    """Visitors cannot save queries."""
    from community_insights.models import SavedQuery

    page = client.get("/s/o~r/contributors/").content.decode()
    assert "Name of this query" not in page
    client.post("/s/o~r/contributors/", {"action": "save", "name": "x"})
    assert not SavedQuery.objects.exists()


def test_submit_with_the_donated_tokens(world, client, monkeypatch):
    """Submit with the donated tokens."""
    fake = FakeClient(repositories=[repo("new/tool", 3), {**repo("new/secret"), "isPrivate": True}])
    monkeypatch.setattr("community_insights.github.Client", lambda token: fake)
    response = client.post("/explore/submit/", {"target": "https://github.com/new/tool"})
    assert response["Location"] == "/s/new~tool/"
    assert Repository.objects.filter(full_name="new/tool").exists()
    assert not Project.objects.filter(target="new/tool").exists(), "no account, no project"
    refused = client.post("/explore/submit/", {"target": "new/secret"}, follow=True)
    assert b"was not found" in refused.content, "the donated token does not tell"
    assert b"Private repositories" not in refused.content and b"is private" not in refused.content
    bad = client.post("/explore/submit/", {"target": "a/b/c"}, follow=True)
    assert b"Not a repository or organisation" in bad.content
    whole = client.post("/explore/submit/", {"target": "new"})
    assert whole["Location"] == "/s/new/"
    assert not Repository.objects.filter(full_name="new/secret").exists()


def test_a_visitor_fetches_with_the_donated_tokens(world, client, monkeypatch):
    """A visitor fetches with the donated tokens."""
    fake = FakeClient(issues=[item(1, "a", "2026-01-01T00:00:00Z")])
    monkeypatch.setattr("community_insights.github.Client", lambda token: fake)
    page = client.get("/s/o~empty/fetch/").content.decode()
    assert "the tokens people donated to it" in page and 'name="priority"' not in page
    client.post("/s/o~empty/fetch/", {"next": "/s/o~empty/", "priority": "10"})
    job = FetchJob.objects.get(repository__full_name="o/empty", status=FetchJob.DONE)
    assert job.user is None and job.priority == FetchJob.LOW
    assert job.points_used > 0, "read with the token alice shares"


def test_without_donated_tokens_without_a_token(world, client, monkeypatch):
    """Without donated tokens without a token."""
    from community_insights.models import AccessToken

    from ..fakes.rest import FakeREST

    AccessToken.objects.all().delete()
    monkeypatch.setattr("community_insights.pipeline.runner.AnonymousClient", FakeREST)

    class Totals:
        """Totals without a token: one issue each."""

        requests = 0

        async def totals(self, names):
            """No pull request and one issue for each repository."""
            return dict.fromkeys(names, (0, 1))

        async def close(self):
            """Nothing to close."""
            pass

    monkeypatch.setattr("community_insights.github.anonymous.AnonymousClient", Totals)
    client.post("/s/o~empty/fetch/", {"next": "/s/o~empty/"})
    assert FetchJob.objects.get(repository__full_name="o/empty", status=FetchJob.DONE).user is None


def test_the_demo_is_shown_only_while_there_is_nothing_else(client):
    """The demo is shown only while there is nothing else."""
    from community_insights.demo import DEMO

    store_repository(repo(DEMO))
    assert DEMO in client.get("/explore/").content.decode()
    store_repository(repo("o/real"))
    page = client.get("/explore/").content.decode()
    assert "o/real" in page and DEMO not in page
