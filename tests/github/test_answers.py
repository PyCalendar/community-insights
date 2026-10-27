"""The answers of GitHub become the errors that explain them."""

import pytest

from community_insights import errors

from ..fakes import Response, answering, run

PLONE_REFUSAL = (
    "The 'plone' organization forbids access via a fine-grained personal access tokens "
    "if the token's lifetime is greater than 366 days."
)


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        (Response(401), errors.InvalidAPIToken),
        (
            Response(
                401, headers={"github-authentication-token-expiration": "2020-01-01 00:00:00 UTC"}
            ),
            errors.ExpiredAPIToken,
        ),
        (
            Response(
                403,
                text=PLONE_REFUSAL,
            ),
            errors.TokenLifetimeRefused,
        ),
        (
            Response(403, text="Resource not accessible by personal access token"),
            errors.TokenNotAllowed,
        ),
        (
            Response(
                200,
                body={
                    "errors": [{"type": "FORBIDDEN", "message": "lifetime is greater than 90 days"}]
                },
            ),
            errors.TokenLifetimeRefused,
        ),
        (Response(502), errors.GitHubUnreachable),
        (Response(400, text="bad"), errors.GitHubError),
        (
            Response(200, body={"errors": [{"type": "SOMETHING", "message": "odd"}]}),
            errors.GitHubError,
        ),
    ],
)
def test_github_answers_become_errors(response, expected):
    with pytest.raises(expected):
        run(answering(response).graphql, "query { x }")


def test_unreachable_github():
    import niquests

    client = answering(niquests.ConnectionError("no route"))
    with pytest.raises(errors.GitHubUnreachable):
        run(client.graphql, "query { x }")


def test_not_json():
    with pytest.raises(errors.GitHubError, match="not JSON"):
        run(answering(Response(body=ValueError("not json"))).graphql, "query { x }")


def test_secondary_rate_limit_waits_and_tries_again(monkeypatch):
    waited = []

    async def sleep(seconds):
        waited.append(seconds)

    monkeypatch.setattr("community_insights.github.client.asyncio.sleep", sleep)
    slow = Response(
        403, text="You have exceeded a secondary rate limit", headers={"retry-after": "3"}
    )
    client = answering(slow, Response(body={"data": {"x": 1}}))
    assert run(client.graphql, "query { x }") == {"x": 1}
    assert waited == [3]


def test_long_secondary_waits_are_left_to_the_pool(monkeypatch):
    async def sleep(seconds):
        raise AssertionError("must not wait that long")

    monkeypatch.setattr("community_insights.github.client.asyncio.sleep", sleep)
    slow = Response(429, headers={"retry-after": "600"})
    with pytest.raises(errors.SecondaryRateLimitExceeded) as error:
        run(answering(slow).graphql, "query { x }")
    assert error.value.retry_after == 600


def test_secondary_rate_limit_without_retry_after_backs_off(monkeypatch):
    waited = []

    async def sleep(seconds):
        waited.append(seconds)

    monkeypatch.setattr("community_insights.github.client.asyncio.sleep", sleep)
    slow = Response(403, text="secondary rate limit")
    client = answering(slow, slow, Response(body={"data": {}}))
    run(client.graphql, "query { x }")
    assert waited == [1, 2]
