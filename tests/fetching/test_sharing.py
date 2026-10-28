"""Sharing the points of tokens with everybody on the site."""

from datetime import timedelta

import pytest
from django.utils import timezone

from community_insights.models import AccessToken
from community_insights.tokens import Entry, NoTokenLeft, TokenPool
from tests.factories import AccessTokenFactory, UserFactory

from ..fakes import Counting, FakeClient, run

pytestmark = pytest.mark.django_db


def test_the_model_computes_the_numbers_of_the_sliders(user):  # noqa: F811
    """The same numbers as tests/js/token-sliders.test.js."""
    token = AccessTokenFactory(user=user)
    assert (token.max_points, token.shared_points, token.reserve) == (5000, 500, 0)
    token.max_percent, token.shared_percent = 90, 10
    assert (token.max_points, token.shared_points, token.reserve) == (4500, 450, 500)
    token.rate_limit, token.max_percent, token.shared_percent = 15000, 10, 50
    assert (token.max_points, token.shared_points, token.reserve) == (1500, 750, 13500)


def test_shared_points_of_others_come_after_the_own_tokens(user):  # noqa: F811
    """Shared points of others come after the own tokens."""
    from community_insights.tokens import entries_for

    AccessTokenFactory(user=user, label="own")
    friend = UserFactory(username="bob")
    AccessToken.objects.create(user=friend, token="f", login="bob", shared_percent=10)
    AccessToken.objects.create(
        user=UserFactory(username="eve"), token="e", login="eve", shared_percent=0
    )
    entries = entries_for(user, lambda token: FakeClient())
    assert [(e.label, e.shared) for e in entries] == [("own", False), ("shared by bob", True)]


def test_others_use_only_the_shared_points(user):  # noqa: F811
    """Others use only the shared points."""
    friend = UserFactory(username="bob")
    token = AccessToken.objects.create(
        user=friend,
        token="f",
        login="bob",
        rate_limit=100,
        shared_percent=3,  # 3 points
    )
    mine, theirs = Counting("mine"), Counting("theirs")
    pool = TokenPool([Entry("shared", theirs, token, shared=True)])
    for _ in range(3):
        run(pool.graphql, "query { x }")
    with pytest.raises(NoTokenLeft):
        run(pool.graphql, "query { x }")
    token.refresh_from_db()
    assert (token.used_in_hour, token.used_by_others_in_hour) == (3, 3)
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
        user=UserFactory(username="bob"), token="f", login="bob", rate_limit=100, shared_percent=10
    )
    entries = [Entry("own", Counting("a"), own), Entry("bob", Counting("b"), friend, shared=True)]
    assert points_left(entries, timezone.now()) == {
        "own": 50,
        "shared": 10,
        "total": 60,
        "unlimited": False,
    }
