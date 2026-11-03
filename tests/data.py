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


def replies_client() -> FakeClient:
    """A fake GitHub whose pull requests are answered or not, for the page of replies.

    ann answers both reviews, with a commit and a comment; ben does not answer his only one,
    which maint closes; cid answers one of two, maint pushing to the other does not count;
    dot gets no feedback; a bot opens one; eve hears only from coveralls, a bot by its handle;
    fay closes her own without answering; PR 12 is read without commits; ann leaves a comment
    on PR 13 unanswered, but it was merged; gil only gets an approval; rae answers the review
    of maint with a review comment, which GitHub keeps as a review of hers.
    """
    review = node("maint", "2026-01-05T12:00:00Z", "MEMBER", key="submittedAt")
    said = node("maint", "2026-01-05T12:00:00Z", "MEMBER")
    return FakeClient(
        prs=[
            item(1, "ann", T0, reviews=[review], commits=[("ann", "2026-01-05T13:00:00Z")]),
            item(
                2,
                "ann",
                T0,
                comments=[said, node("ann", "2026-01-06T09:00:00Z")],
                reviews=[],
                commits=[("ann", T0)],
            ),
            item(
                3,
                "ben",
                T0,
                reviews=[review],
                state="CLOSED",
                closer="maint",
                commits=[("ben", T0)],
            ),
            item(
                4,
                "cid",
                T0,
                comments=[node("cid", "2026-01-05T11:00:00Z"), said],
                reviews=[],
                commits=[("cid", T0), ("maint", "2026-01-06T09:00:00Z")],
            ),
            item(
                5,
                "cid",
                T0,
                comments=[node("ci[bot]", "2026-01-05T10:10:00Z", typename="Bot")],
                reviews=[],
                commits=[("cid", T0)],
            ),
            item(6, "cid", T0, reviews=[review], commits=[("cid", "2026-01-07T09:00:00Z")]),
            item(7, "dot", T0, reviews=[], commits=[("dot", T0)]),
            item(
                8,
                "dependabot[bot]",
                T0,
                comments=[said],
                reviews=[],
                commits=[("dependabot[bot]", T0)],
            ),
            item(
                9,
                "eve",
                T0,
                comments=[node("coveralls", "2026-01-05T10:30:00Z")],
                reviews=[],
                commits=[("eve", T0)],
            ),
            item(
                10,
                "fay",
                T0,
                comments=[said],
                reviews=[],
                state="CLOSED",
                closer="fay",
                commits=[("fay", T0)],
            ),
            item(
                11,
                "Bobby",
                "2026-03-01T10:00:00Z",
                comments=[said],
                reviews=[],
                commits=[("Bobby", "2026-03-02T10:00:00Z")],
            ),
            item(12, "bob", "2026-03-01T10:00:00Z", comments=[said], reviews=[]),
            item(
                13,
                "ann",
                T0,
                comments=[said],
                reviews=[],
                state="CLOSED",
                merged=True,
                closer="maint",
                commits=[("ann", T0)],
            ),
            item(
                14,
                "gil",
                T0,
                reviews=[
                    node(
                        "maint", "2026-01-05T12:00:00Z", "MEMBER", "User", "submittedAt", "APPROVED"
                    )
                ],
                commits=[("gil", T0)],
            ),
            item(
                15,
                "rae",
                T0,
                reviews=[
                    node(
                        "maint",
                        "2026-01-05T12:00:00Z",
                        "MEMBER",
                        "User",
                        "submittedAt",
                        "CHANGES_REQUESTED",
                    ),
                    node(
                        "rae",
                        "2026-01-05T13:00:00Z",
                        "CONTRIBUTOR",
                        "User",
                        "submittedAt",
                        "COMMENTED",
                    ),
                ],
                commits=[("rae", T0)],
            ),
        ],
        issues=[item(1, "ann", T0, comments=[said])],
    )


@pytest.fixture
def replied(user):
    """A public repository o/r in a project of the user, read from ``replies_client``."""
    repository = store_repository(repo("o/r", 5))
    read_repository(replies_client(), repository)
    project = ProjectFactory(user=user, target="o/r", repositories=[repository])
    return {"user": user, "project": project, "repository": repository}
