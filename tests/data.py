"""Fixtures: a user with a synced project, classes, tokens and jobs."""

import pytest
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
from django.contrib.auth import get_user_model

from community_insights.classify import ensure_default_classes
from community_insights.models import Project
from community_insights.sync import read_repository, store_repository

from .factories import AccessTokenFactory, FetchJobFactory, ProjectFactory
from .fakes import FakeClient, commit, item, node, repo, set_time_zone

T0 = "2026-01-05T10:00:00Z"  # a Monday


def full_client() -> FakeClient:
    """A fake GitHub with pull requests, issues, people, repositories and commits."""
    return FakeClient(
        prs=[
            item(
                1,
                "bob",
                T0,
                comments=[
                    node("ci[bot]", "2026-01-05T10:10:00Z", typename="Bot"),
                    node("bob", "2026-01-05T10:20:00Z"),
                ],
                reviews=[node("maint", "2026-01-05T12:00:00Z", "MEMBER", key="submittedAt")],
                state="CLOSED",
                merged=True,
                updated="2026-01-05T12:00:00Z",
            ),
            item(2, "carol", "2026-01-06T09:00:00Z", reviews=[]),
            item(3, "carol", "2026-01-07T09:00:00Z", reviews=[], state="CLOSED"),
        ],
        issues=[
            item(1, "bob", T0, comments=[node("dave", "2026-01-07T10:00:00Z")]),
            item(2, "ghost-less", "2026-02-01T08:00:00Z"),
        ],
        people={"bob": {"login": "bob", "name": "Bob", "location": "Berlin", "avatarUrl": ""}},
        repositories=[repo("o/r", 5), repo("o/empty", 0)],
        commits=[
            commit("1" * 40, "bob", "2026-01-04T09:00:00Z"),
            commit("2" * 40, "maint", "2026-01-05T11:00:00Z"),
        ],
    )


@pytest.fixture
def user(db):
    """A user with the default classes of people."""
    user = get_user_model().objects.create_user("alice", "alice@example.org", "pw")
    ensure_default_classes(user)
    return user


@pytest.fixture
def world(user):
    """A synced project, an empty one, a token and jobs in every state."""
    client = full_client()
    synced = store_repository(repo("o/r", 5))
    read_repository(client, synced)
    empty = store_repository(repo("o/empty", 0))
    project = ProjectFactory(user=user, target="o/r", repositories=[synced])
    nothing = ProjectFactory(user=user, target="o/empty", repositories=[empty])
    AccessTokenFactory(user=user, token="t", label="mine")
    for status in ("queued", "running", "done", "failed", "cancelled", "limit"):
        FetchJobFactory(
            user=user,
            repository=synced,
            status=status,
            reason=f"test {status}",
            reason_url=f"/s/{project.pk}/",
        )
    return {"user": user, "project": project, "empty": nothing, "repository": synced}


@pytest.fixture
def signed_in(client, user):
    """A client signed in as the user, with a linked GitHub account, in Tokyo."""
    app = SocialApp.objects.create(provider="github", name="gh", client_id="i", secret="s")
    from django.contrib.sites.models import Site

    app.sites.add(Site.objects.get_current())
    account = SocialAccount.objects.create(
        user=user, provider="github", uid="1", extra_data={"login": "alice"}
    )
    SocialToken.objects.create(app=app, account=account, token="tok")
    client.force_login(user)
    set_time_zone(client, "Asia/Tokyo")
    return client


@pytest.fixture
def synced(user):
    """A repository with pull requests and issues, synced with the fake client."""
    client = FakeClient(
        prs=[
            item(
                1,
                "bob",
                T0,
                comments=[
                    node("ci[bot]", "2026-01-05T10:10:00Z", typename="Bot"),
                    node("bob", "2026-01-05T10:20:00Z"),
                ],
                reviews=[node("maint", "2026-01-05T12:00:00Z", "MEMBER", key="submittedAt")],
                state="CLOSED",
                merged=True,
                updated="2026-01-05T12:00:00Z",
            ),
            item(2, "carol", "2026-01-06T09:00:00Z", reviews=[]),
        ],
        issues=[
            item(1, "bob", T0, comments=[node("dave", "2026-01-07T10:00:00Z")]),
        ],
        people={"bob": {"login": "bob", "name": "Bob", "location": "Berlin", "avatarUrl": "x"}},
    )
    data = repo("o/r", stars=5)
    repository = store_repository(data)
    project = Project.objects.create(user=user, target="o/r")
    project.repositories.add(repository)
    read_repository(client, repository)
    return repository
