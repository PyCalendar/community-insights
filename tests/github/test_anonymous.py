"""Reading public repositories without a token."""

from datetime import UTC, datetime, timedelta

import pytest

from community_insights import errors
from community_insights.github.anonymous import SERVER_QUOTA
from community_insights.models import Event, FetchJob, Item
from community_insights.sync import Syncer, store_repository
from community_insights.sync.sources import AnonymousSource

from ..fakes import Response, repo, run
from ..fakes.rest import FakeREST, rest_comment, rest_issue
from ..fakes.session import answering_rest

pytestmark = pytest.mark.django_db


def rest_data():
    """A fake REST API with pull requests, issues, comments and reviews."""
    return FakeREST(
        issues=[
            rest_issue(1, "bob", "2026-01-05T10:00:00Z", pull=True, merged=True, state="closed"),
            rest_issue(2, "carol", "2026-01-06T10:00:00Z"),
        ],
        comments=[
            rest_comment(1, "ci", "2026-01-05T10:10:00Z", kind="Bot"),
            rest_comment(2, "dave", "2026-01-07T10:00:00Z", association="NONE"),
        ],
        reviews=[rest_comment(1, "maint", "2026-01-05T12:00:00Z", review=True)],
    )


@pytest.fixture
def quota():
    """The quota of the server, restored after the test."""
    saved = (SERVER_QUOTA.limit, SERVER_QUOTA.remaining, SERVER_QUOTA.reset_at)
    yield SERVER_QUOTA
    SERVER_QUOTA.limit, SERVER_QUOTA.remaining, SERVER_QUOTA.reset_at = saved


def test_items_comments_and_reviews_without_a_token(db):
    """Items comments and reviews without a token."""
    repository = store_repository(repo("o/r"))
    rest = rest_data()
    message = run(Syncer(AnonymousSource(rest)).sync, repository)
    assert message == "1 pull requests, 1 issues and 0 commits read"
    pr = Item.objects.get(kind="pr")
    assert pr.merged and pr.state == "closed"
    kinds = sorted(pr.events.values_list("actor", "kind", "is_bot"))
    assert kinds == [("bob", "opened", False), ("ci", "comment", True), ("maint", "review", False)]
    assert Item.objects.get(kind="issue").events.filter(actor="dave").exists()
    assert rest.requests == 4, "issues, comments, review comments and commits: four requests"


def test_later_fetches_add_the_new_comments(db):
    """Later fetches add the new comments."""
    repository = store_repository(repo("o/r"))
    rest = rest_data()
    run(Syncer(AnonymousSource(rest)).sync, repository)
    repository.refresh_from_db()
    rest.issues[1]["updated_at"] = "2026-02-01T00:00:00Z"
    rest.comments.append(rest_comment(2, "erin", "2026-02-01T00:00:00Z"))
    run(Syncer(AnonymousSource(rest)).sync, repository)
    actors = sorted(Item.objects.get(kind="issue").events.values_list("actor", flat=True))
    assert actors == ["carol", "dave", "erin"], "the old comment stays, the new one is added"
    # only what changed since the older of the two kinds was read
    assert rest.asked[-1][1]["since"].startswith("2026-01-05T10:00")


def test_people_without_a_token_have_no_names(db):
    """People without a token have no names."""
    from community_insights.models import Person

    repository = store_repository(repo("o/r"))
    run(Syncer(AnonymousSource(rest_data())).sync, repository)
    assert Person.objects.get(login="bob").name == ""


def test_the_quota_of_the_server_is_noted_and_respected(quota):
    """The quota of the server is noted and respected."""
    reset = int((datetime.now(UTC) + timedelta(minutes=20)).timestamp())
    headers = {
        "x-ratelimit-limit": "60",
        "x-ratelimit-remaining": "0",
        "x-ratelimit-reset": str(reset),
    }
    client = answering_rest(Response(body=[], headers=headers))
    assert run(client.all_pages, "/repos/o/r/issues") == []
    assert quota.remaining == 0
    with pytest.raises(errors.AllTokensUsedUp):
        run(client.get, "/repos/o/r/issues")


def test_rest_errors(quota):
    """Rest errors."""
    quota.remaining = None
    with pytest.raises(errors.RepositoryNotFound):
        run(answering_rest(Response(404)).get, "/repos/o/missing")
    with pytest.raises(errors.RateLimitExceeded):
        run(answering_rest(Response(403, headers={"x-ratelimit-remaining": "0"})).get, "/repos/o/r")
    quota.remaining = None
    with pytest.raises(errors.GitHubUnreachable):
        run(answering_rest(Response(503)).get, "/repos/o/r")


def test_pages_of_100(quota):
    """Pages of 100."""
    quota.remaining = None
    full = Response(body=[{"n": i} for i in range(100)])
    client = answering_rest(full, Response(body=[{"n": 100}]))
    assert len(run(client.all_pages, "/repos/o/r/issues")) == 101


def test_repository_in_the_shape_of_graphql(quota):
    """Repository in the shape of graphql."""
    quota.remaining = None
    client = answering_rest(
        Response(body={"full_name": "o/r", "stargazers_count": 3, "private": False})
    )
    assert run(client.repository, "o/r")["nameWithOwner"] == "o/r"


def test_a_user_without_tokens_reads_without_a_token(world, signed_in, monkeypatch, quota):  # noqa: F811
    """A user without tokens reads without a token."""
    from allauth.socialaccount.models import SocialToken

    from community_insights.models import AccessToken

    SocialToken.objects.all().delete()
    AccessToken.objects.all().delete()
    quota.remaining = None
    monkeypatch.setattr("community_insights.pipeline.runner.AnonymousClient", rest_data)
    pk = world["empty"].pk

    class Totals:
        """Totals without a token: one of each."""

        requests = 0

        async def totals(self, names):
            """One pull request and one issue for each repository."""
            return dict.fromkeys(names, (1, 1))

        async def close(self):
            """Nothing to close."""
            pass

    monkeypatch.setattr("community_insights.github.anonymous.AnonymousClient", Totals)
    page = signed_in.get(f"/s/{pk}/fetch/").content.decode()
    assert "You have no token" in page
    signed_in.post(f"/s/{pk}/fetch/", {"next": f"/s/{pk}/"})
    job = FetchJob.objects.get(repository__full_name="o/empty", status="done")
    assert job.points_used == 4  # issues, comments, review comments, commits
    assert Event.objects.filter(item__repository__full_name="o/empty").exists()


def test_without_a_token_the_rest_api_is_asked():
    """The REST requests ask for the JSON of GitHub, with the parameters."""
    sent: list = []
    client = answering_rest(Response(body={"ok": True}), sent=sent)
    assert run(client.get, "/repos/o/r", per_page=5) == {"ok": True}
    assert sent[0][0] == "https://api.github.com/repos/o/r?per_page=5"


def test_without_a_token_unreachable_github():
    """A connection that fails is shown as GitHub being unreachable."""
    import httpx

    with pytest.raises(errors.GitHubUnreachable):
        run(answering_rest(httpx.ConnectError("no route")).get, "/repos/o/r")


def test_without_a_token_a_refused_request_says_why():
    """Another answer of 4xx is shown with its text."""
    with pytest.raises(errors.GitHubRequestRejected, match="422: bad parameter"):
        run(answering_rest(Response(422, text="bad parameter")).get, "/repos/o/r")


def test_without_a_token_the_text_rate_limit_counts_as_used_up(quota):
    """A 403 that says rate limit is a used up quota, also with points left."""
    slow = Response(403, text="API rate limit exceeded", headers={"x-ratelimit-remaining": "5"})
    with pytest.raises(errors.RateLimitExceeded):
        run(answering_rest(slow).get, "/repos/o/r")


def test_the_search_has_a_quota_of_its_own(quota):
    """An answer of the search does not change the quota of the server."""
    quota.remaining = 50
    used = Response(body={"items": []}, headers={"x-ratelimit-remaining": "1"})
    run(answering_rest(used).get, "/search/issues", q="x")
    assert quota.remaining == 50
