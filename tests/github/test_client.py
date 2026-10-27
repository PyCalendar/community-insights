"""The GitHub client, with the HTTP session mocked."""

from datetime import UTC, datetime

import pytest

from community_insights.errors import GitHubError, RepositoryNotFound, TokenError
from community_insights.github import Client, RateLimited, parse_expiration
from community_insights.github.reads import repositories

from ..fakes import Response, answering, run

pytestmark = pytest.mark.django_db


def page(names, more):
    nodes = [{"nameWithOwner": n} for n in names]
    info = {"hasNextPage": more, "endCursor": "c"}
    return Response(body={"data": {"viewer": {"repositories": {"nodes": nodes, "pageInfo": info}}}})


def test_sends_token_and_returns_data():
    sent = []
    client = answering(Response(body={"data": {"x": 1}}), sent=sent)
    assert run(client.graphql, "query { x }") == {"x": 1}
    assert client.session.headers["Authorization"] == "Bearer secret"
    assert sent[0][0] == "https://api.github.com/graphql"
    assert client.requests == 1


def test_rejected_token():
    with pytest.raises(TokenError):
        run(answering(Response(401)).graphql, "query { x }")


def test_errors_but_not_missing_users():
    ok = Response(body={"data": {"u0": None}, "errors": [{"type": "NOT_FOUND", "message": "x"}]})
    assert run(answering(ok).people, ["ghost"]) == {"ghost": None}
    bad = Response(body={"errors": [{"type": "OTHER", "message": "boom"}]})
    with pytest.raises(GitHubError, match="boom"):
        run(answering(bad).graphql, "query { x }")


def test_repositories_are_read_page_by_page():
    sent = []
    client = answering(page(["a/1", "a/2"], True), page(["a/3"], False), sent=sent)
    assert [r["nameWithOwner"] for r in run(client.repositories)] == ["a/1", "a/2", "a/3"]
    assert sent[1][1]["variables"]["after"] == "c"


def test_reads_work_with_any_graphql_function():
    async def graphql(query, **variables):
        return {
            "viewer": {
                "repositories": {
                    "nodes": [{"nameWithOwner": "x/y"}],
                    "pageInfo": {"hasNextPage": False},
                }
            }
        }

    assert run(repositories, graphql) == [{"nameWithOwner": "x/y"}]


def test_missing_repository():
    client = answering(Response(body={"data": {"repository": None}}))
    with pytest.raises(RepositoryNotFound, match="not found"):
        run(client.repository, "a/b")


def test_many_repositories_are_asked_in_batches_at_the_same_time():
    names = [f"o/r{i}" for i in range(120)]
    sent = []
    answers = [Response(body={"data": {f"r{i}": {"id": 1} for i in range(50)}}) for _ in range(3)]
    client = answering(*answers, sent=sent)
    found = run(client.visible, names)
    assert len(sent) == 3 and all(found.values()) and len(found) == 120


def test_client_closes():
    run(Client("t").close)


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("2026-11-30 12:00:00 UTC", datetime(2026, 11, 30, 12, tzinfo=UTC)),
        ("2026-11-30 13:00:00 +0100", datetime(2026, 11, 30, 12, tzinfo=UTC)),
        ("", None),
        (None, None),
        ("soon", None),
    ],
)
def test_token_expiration_header(header, expected):
    assert parse_expiration(header) == expected


def test_client_notes_rate_limit_and_expiry():
    client = answering(
        Response(
            body={"data": {}},
            headers={
                "x-ratelimit-limit": "5000",
                "x-ratelimit-remaining": "4999",
                "x-ratelimit-reset": "1800000000",
                "github-authentication-token-expiration": "2027-01-01 00:00:00 UTC",
            },
        )
    )
    run(client.graphql, "query { x }")
    assert (client.rate.limit, client.rate.remaining) == (5000, 4999)
    assert client.rate.reset_at == datetime.fromtimestamp(1800000000, UTC)
    assert client.rate.expires_at == datetime(2027, 1, 1, tzinfo=UTC)


@pytest.mark.parametrize(
    "response",
    [
        Response(403, headers={"x-ratelimit-remaining": "0"}),
        Response(200, body={"errors": [{"type": "RATE_LIMITED", "message": "x"}]}),
    ],
)
def test_client_rate_limits(response):
    with pytest.raises(RateLimited):
        run(answering(response).graphql, "query { x }")


def test_queries_escape_repository_names():
    sent = []
    client = answering(Response(body={"data": {"r0": None}}), sent=sent)
    assert run(client.visible, ['a"b/c\\d']) == {'a"b/c\\d': False}
    query = sent[0][1]["query"]
    assert 'owner: "a\\"b"' in query and 'name: "c\\\\d"' in query
