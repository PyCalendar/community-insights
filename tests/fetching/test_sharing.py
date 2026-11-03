"""Sharing the points of tokens with everybody on the site."""

from datetime import timedelta

import pytest
from django.utils import timezone

from community_insights.models import AccessToken, TokenGrant
from community_insights.tokens import Entry, NoTokenLeft, TokenPool
from tests.factories import AccessTokenFactory, UserFactory
from tests.factories.access_token import share

from ..fakes import Counting, FakeClient, run

pytestmark = pytest.mark.django_db


def test_the_model_computes_the_numbers_of_the_sliders(user):  # noqa: F811
    """The same numbers as tests/js/token-sliders.test.js."""
    token = AccessTokenFactory(user=user)
    everybody = token.grants.get()
    assert (token.max_points, everybody.points, token.reserve) == (5000, 500, 0)
    token.max_percent = 90
    assert (token.max_points, everybody.points, token.reserve) == (4500, 450, 500)
    token.rate_limit, token.max_percent, everybody.percent = 15000, 10, 50
    assert (token.max_points, everybody.points, token.reserve) == (1500, 750, 13500)


def test_shared_points_of_others_come_after_the_own_tokens(user):  # noqa: F811
    """Shared points of others come after the own tokens."""
    from community_insights.tokens import entries_for

    AccessTokenFactory(user=user, label="own")
    friend = UserFactory(username="bob")
    share(AccessToken.objects.create(user=friend, token="f", login="bob"), 10)
    AccessToken.objects.create(user=UserFactory(username="eve"), token="e", login="eve")
    entries = entries_for(user, lambda token: FakeClient())
    assert [(e.label, e.shared) for e in entries] == [("own", False), ("shared by bob", True)]


def test_others_use_only_the_shared_points(user):  # noqa: F811
    """Others use only the shared points."""
    friend = UserFactory(username="bob")
    token = AccessToken.objects.create(user=friend, token="f", login="bob", rate_limit=100)
    grant = share(token, 3)  # 3 points
    mine, theirs = Counting("mine"), Counting("theirs")
    pool = TokenPool([Entry("shared", theirs, token, grant=grant)])
    for _ in range(3):
        run(pool.graphql, "query { x }")
    with pytest.raises(NoTokenLeft):
        run(pool.graphql, "query { x }")
    token.refresh_from_db()
    grant.refresh_from_db()
    assert (token.used_in_hour, grant.used_in_hour) == (3, 3)
    assert theirs.requests == 3 and mine.requests == 0


def test_the_reserve_stays_with_github(user):  # noqa: F811
    """The reserve stays with github."""
    token = AccessTokenFactory(user=user, rate_limit=5000, max_percent=90)  # stop when 500 are left
    token.rate_remaining = 501
    token.rate_reset_at = timezone.now() + timedelta(minutes=30)
    assert token.owner_left(timezone.now()) == 1
    token.rate_remaining = 500
    assert token.owner_left(timezone.now()) == 0


def test_points_allowed_above_the_maximum_for_this_hour(user):  # noqa: F811
    """Points allowed above the maximum for this hour."""
    from community_insights.models import Profile
    from community_insights.tokens import HourAllowance

    profile = Profile.of(user)
    token = AccessTokenFactory(user=user, rate_limit=100, max_percent=1)  # 1 point per hour
    entry = Entry("own", Counting("a"), token, allowance=HourAllowance(profile))
    pool = TokenPool([entry])
    run(pool.graphql, "query { x }")
    with pytest.raises(NoTokenLeft):
        run(pool.graphql, "query { x }")
    profile.allow_extra(2, timezone.now())
    profile.save()
    run(pool.graphql, "query { x }")
    run(pool.graphql, "query { x }")
    with pytest.raises(NoTokenLeft):
        run(pool.graphql, "query { x }")
    profile.refresh_from_db()
    assert profile.extra_used == 2
    profile.extra_from = timezone.now() - timedelta(hours=2)
    assert profile.extra_left(timezone.now()) == 0  # only for the hour


def test_points_left(user):  # noqa: F811
    """Points left."""
    from community_insights.tokens import points_left

    own = AccessTokenFactory(user=user, rate_limit=100, max_percent=50)
    friend = AccessToken.objects.create(
        user=UserFactory(username="bob"), token="f", login="bob", rate_limit=100
    )
    grant = share(friend, 10)
    entries = [Entry("own", Counting("a"), own), Entry("bob", Counting("b"), friend, grant=grant)]
    assert points_left(entries, timezone.now()) == {
        "own": 50,
        "shared": 10,
        "total": 60,
        "unlimited": False,
    }


def grant_of(login: str, kind: str, scope: str = "", badge: str = "", percent: int = 10):
    """A token of somebody else with one public use and no share for everybody.

    Args:
        login: Whose token it is.
        kind: The kind of the grant.
        scope: Its public scope.
        badge: The person of one badge, "" for all.
        percent: Its share.

    Returns:
        The grant.
    """
    token = AccessTokenFactory(user=UserFactory(username=login), login=login, shared_percent=0)
    return TokenGrant.objects.create(
        token=token, kind=kind, scope=scope, login=badge, percent=percent
    )


def test_grants_of_a_scope_are_used_only_for_it(user):  # noqa: F811
    """A badge of o~r may use the grants for its badges, not the others."""
    from community_insights.tokens import entries_for
    from community_insights.tokens.use import Use

    grant_of("org", TokenGrant.BADGES, "o")
    grant_of("one", TokenGrant.BADGES, "o~r", badge="cid")
    grant_of("pages", TokenGrant.PAGES, "o~r")
    grant_of("else", TokenGrant.BADGES, "x~y")

    def labels(use):
        """The tokens a fetch for the use may read with."""
        return [e.label for e in entries_for(None, lambda token: FakeClient(), use=use)]

    assert labels(None) == []
    assert labels(Use(TokenGrant.BADGES, "o~r", "cid")) == ["shared by org", "shared by one"]
    assert labels(Use(TokenGrant.BADGES, "o~r", "ben")) == ["shared by org"]
    assert labels(Use(TokenGrant.PAGES, "o~r")) == ["shared by pages"]
    assert labels(Use(TokenGrant.VISITORS, "o~r")) == []


def test_each_grant_has_its_own_budget(user):  # noqa: F811
    """A token with two grants: each counts its own points, the token counts all."""
    token = AccessTokenFactory(user=UserFactory(username="bob"), rate_limit=100, shared_percent=2)
    everybody = token.grants.get()
    badges = TokenGrant.objects.create(token=token, kind=TokenGrant.BADGES, scope="o", percent=1)
    pool = TokenPool([Entry("b", Counting("b"), token, grant=badges)])
    run(pool.graphql, "query { x }")
    with pytest.raises(NoTokenLeft):
        run(pool.graphql, "query { x }")
    now = timezone.now()
    for grant in (everybody, badges):
        grant.refresh_from_db()
    token.refresh_from_db()
    assert (badges.used(now), everybody.used(now), everybody.left(now)) == (1, 0, 2)
    assert token.used_in_hour == 1


def test_the_shares_move_into_grants(transactional_db):
    """The migration of the grants keeps the share of each token for everybody."""
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor

    executor = MigrationExecutor(connection)
    before = [("community", "0010_review_state_and_details")]
    executor.migrate(before)
    old = executor.loader.project_state(before).apps
    user = old.get_model("auth", "User").objects.create(username="kim")
    old.get_model("community", "AccessToken").objects.create(
        user=user, token="t", login="kim", shared_percent=30, used_by_others_in_hour=4, order=0
    )
    old.get_model("community", "AccessToken").objects.create(
        user=user, token="u", login="kim", shared_percent=0, order=1
    )
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())
    grants = list(TokenGrant.objects.values_list("kind", "percent", "used_in_hour"))
    assert grants == [(TokenGrant.EVERYBODY, 30, 4)]
