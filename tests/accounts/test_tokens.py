"""The page GitHub access: tokens, their order, limits and tests."""

from datetime import UTC, datetime

import pytest
from django.db import connection

from community_insights.models import AccessToken

from ..fakes import Answering, FakeClient

pytestmark = pytest.mark.django_db


def test_add_tokens_in_order_with_limits(world, signed_in, monkeypatch):  # noqa: F811
    """Add tokens in order with limits."""
    expires = datetime(2027, 1, 1, tzinfo=UTC)
    monkeypatch.setattr("community_insights.github.Client", lambda token: Answering(token, expires))
    signed_in.post(
        "/dashboard/github/",
        {
            "action": "add",
            "token": "a",
            "label": "Kim",
            "max_percent": "50",
            "shared_percent": "20",
        },
    )
    response = signed_in.post("/dashboard/github/", {"action": "add", "token": "b"}, follow=True)
    assert b"This token never expires" not in response.content  # it expires: no warning
    tokens = list(world["user"].access_tokens.filter(linked=False))
    assert [t.token for t in world["user"].access_tokens.all()] == ["tok", "t", "a", "b"], (
        "the linked account first"
    )
    assert (tokens[1].max_points, tokens[1].shared_points) == (2500, 500)
    assert tokens[1].expires_at == expires
    assert (tokens[2].max_percent, tokens[2].shared_percent) == (100, 10)  # the defaults
    signed_in.post("/dashboard/github/", {"action": "up", "id": tokens[2].pk})
    assert [t.token for t in world["user"].access_tokens.all()] == ["tok", "t", "b", "a"]
    signed_in.post(
        "/dashboard/github/",
        {"action": "share", "id": tokens[1].pk, "max_percent": "10", "shared_percent": "0"},
    )
    changed = AccessToken.objects.get(pk=tokens[1].pk)
    assert (changed.max_points, changed.shared_points) == (500, 0)


@pytest.mark.parametrize(
    "fields",
    [
        {"token": ""},
        {"token": "x", "max_percent": "101"},
        {"token": "x", "shared_percent": "-1"},
        {"token": "x", "max_percent": "abc"},
    ],
)
def test_bad_tokens_are_not_saved(world, signed_in, monkeypatch, fields):  # noqa: F811
    """Bad tokens are not saved."""
    monkeypatch.setattr("community_insights.github.Client", lambda token: Answering(token))
    before = AccessToken.objects.filter(linked=False).count()
    response = signed_in.post("/dashboard/github/", {"action": "add", **fields}, follow=True)
    assert b"Not saved" in response.content
    assert AccessToken.objects.filter(linked=False).count() == before


def test_rejected_token_is_not_saved(world, signed_in, monkeypatch):  # noqa: F811
    """Rejected token is not saved."""
    from community_insights.github import TokenError

    monkeypatch.setattr(
        "community_insights.github.Client", lambda token: Answering(token, fail=TokenError("bad"))
    )
    response = signed_in.post("/dashboard/github/", {"action": "add", "token": "x"}, follow=True)
    assert b"bad" in response.content


def test_token_without_expiry_is_warned(world, signed_in, monkeypatch):  # noqa: F811
    """Token without expiry is warned."""
    monkeypatch.setattr("community_insights.github.Client", lambda token: Answering(token))
    response = signed_in.post("/dashboard/github/", {"action": "add", "token": "x"}, follow=True)
    assert b"This token never expires" in response.content


def test_test_a_token_on_my_projects(world, signed_in, monkeypatch):  # noqa: F811
    """Test a token on my projects."""
    monkeypatch.setattr("community_insights.github.Client", lambda token: Answering(token))
    token = world["user"].access_tokens.get()
    response = signed_in.post("/dashboard/github/", {"action": "test", "id": token.pk}, follow=True)
    assert b"cannot read 1 of 2 repositories: o/empty" in response.content
    token.refresh_from_db()
    assert token.last_test["missing"] == ["o/empty"]


def test_profile_limit(world, signed_in):  # noqa: F811
    """Profile limit."""
    signed_in.post("/dashboard/github/", {"action": "profile", "fetch_limit": "800"})
    assert world["user"].profile.fetch_limit == 800


def test_the_linked_account_is_a_token_with_limits(world, signed_in):  # noqa: F811
    """The linked account is a token with limits."""
    from allauth.socialaccount.models import SocialAccount, SocialToken

    from community_insights.tokens import entries_for

    entries = entries_for(world["user"], lambda token: FakeClient())
    assert entries[0].stored.linked and entries[0].label == "linked GitHub account"
    linked = AccessToken.objects.get(linked=True)
    assert linked.token == "tok" and linked.login == "alice"
    # it can be shared and limited, not deleted here
    signed_in.post("/dashboard/github/", {"action": "share", "id": linked.pk, "max_percent": "50"})
    assert AccessToken.objects.get(linked=True).max_points == 2500
    signed_in.post("/dashboard/github/", {"action": "delete", "id": linked.pk})
    assert AccessToken.objects.filter(linked=True).exists()
    # a new token from GitHub replaces the old one; unlinking removes it
    SocialToken.objects.update(token="new")
    entries_for(world["user"], lambda token: FakeClient())
    assert AccessToken.objects.get(linked=True).token == "new"
    SocialAccount.objects.all().delete()
    entries_for(world["user"], lambda token: FakeClient())
    assert not AccessToken.objects.filter(linked=True).exists()


def test_private_repositories_are_asked_for_when_wanted(world, signed_in, settings):  # noqa: F811
    """Private repositories are asked for when wanted."""
    assert settings.SOCIALACCOUNT_PROVIDERS["github"]["SCOPE"] == ["read:user"]
    page = signed_in.get("/dashboard/github/").content.decode()
    assert "Allow reading private repositories" not in page, "for now only public ones"
    settings.PRIVATE_REPOSITORIES = True
    page = signed_in.get("/dashboard/github/").content.decode()
    assert "Allow reading private repositories" in page and "scope=read%3Auser%2Crepo" in page


def test_tokens_are_encrypted_in_the_database(world):  # noqa: F811
    """Tokens are encrypted in the database."""
    token = AccessToken.objects.get()
    with connection.cursor() as cursor:
        cursor.execute("SELECT token FROM community_accesstoken WHERE id = %s", [token.pk])
        stored = cursor.fetchone()[0]
    assert stored != "t" and "t" == AccessToken.objects.get().token


def test_token_order(world):  # noqa: F811
    """Token order."""
    user_ = world["user"]
    second = AccessToken.objects.create(user=user_, token="b", login="b")
    second.up()
    assert [t.token for t in user_.access_tokens.all()] == ["b", "t"]


def test_the_demo_project_is_not_tested(world, signed_in, monkeypatch):  # noqa: F811
    """The demo project is not tested."""
    from community_insights.demo import DEMO
    from community_insights.models import Project
    from community_insights.sync import store_repository

    from ..fakes import repo

    project = Project.objects.create(user=world["user"], target=DEMO)
    project.repositories.add(store_repository(repo(DEMO)))
    monkeypatch.setattr("community_insights.github.Client", lambda token: Answering(token))
    token = world["user"].access_tokens.get()
    signed_in.post("/dashboard/github/", {"action": "test", "id": token.pk})
    token.refresh_from_db()
    assert token.last_test["total"] == 2 and DEMO not in token.last_test["missing"]


def test_the_page_says_how_to_create_a_token_before_the_tokens(world, signed_in):  # noqa: F811
    """The page says how to create a token before the tokens."""
    page = signed_in.get("/dashboard/github/").content.decode()
    assert "1. Link GitHub account" in page
    hint = page.index("fine-grained token")
    assert hint < page.index("2. Tokens")
    assert "how-to/tokens.html" in page[hint : page.index("2. Tokens")]
    assert "Suggested limit of API points when a fetch needs more than this" in page
    assert "how-to/tokens.html#points-and-limits" in page
