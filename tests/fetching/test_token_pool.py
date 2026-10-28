"""Tokens used one after the other, each within its limits."""

from datetime import timedelta

import pytest
from django.utils import timezone

from community_insights import errors
from community_insights.github import RateLimited, TokenError
from community_insights.models import AccessToken
from community_insights.tokens import Entry, LimitReached, NoTokenLeft, TokenPool
from tests.factories import AccessTokenFactory

from ..fakes import Counting, run

pytestmark = pytest.mark.django_db


def test_pool_uses_tokens_in_order(user):  # noqa: F811
    """Pool uses tokens in order."""
    first, second = Counting("first"), Counting("second")
    pool = TokenPool(
        [
            Entry("a", first, AccessTokenFactory(user=user)),
            Entry("b", second, AccessTokenFactory(user=user)),
        ]
    )
    run(pool.graphql, "query { x }")
    assert first.requests == 1 and second.requests == 0 and pool.points == 1


def test_pool_skips_a_rate_limited_token(user):  # noqa: F811
    """Pool skips a rate limited token."""
    reset = timezone.now() + timedelta(minutes=30)
    first = Counting("first", fail=RateLimited("used up", reset))
    second = Counting("second")
    a = AccessTokenFactory(user=user)
    pool = TokenPool([Entry("a", first, a), Entry("b", second, AccessTokenFactory(user=user))])
    run(pool.graphql, "query { x }")
    assert second.requests == 1
    a.refresh_from_db()
    assert a.rate_remaining == 0 and a.rate_reset_at == reset and "used up" in a.last_error
    run(pool.graphql, "query { x }")  # the first is not asked again before the reset
    assert second.requests == 2


def test_pool_respects_the_maximum_per_hour(user):  # noqa: F811
    """Pool respects the maximum per hour."""
    first, second = Counting("first"), Counting("second")
    limited = AccessTokenFactory(user=user, rate_limit=100, max_percent=2)  # 2 points per hour
    pool = TokenPool(
        [Entry("a", first, limited), Entry("b", second, AccessTokenFactory(user=user))]
    )
    for _ in range(3):
        run(pool.graphql, "query { x }")
    assert (first.requests, second.requests) == (2, 1)
    limited.refresh_from_db()
    assert limited.used_in_hour == 2


def test_hourly_limit_starts_again_after_an_hour(user):  # noqa: F811
    """Hourly limit starts again after an hour."""
    limited = AccessTokenFactory(
        user=user,
        rate_limit=100,
        max_percent=1,
        used_in_hour=1,
        hour_started=timezone.now() - timedelta(hours=2),
    )
    entry = Entry("a", Counting("a"), limited)
    assert entry.usable(timezone.now())


def test_pool_drops_rejected_tokens(user):  # noqa: F811
    """Pool drops rejected tokens."""
    bad = Counting("bad", fail=TokenError("revoked"))
    good = Counting("good")
    pool = TokenPool(
        [
            Entry("a", bad, AccessTokenFactory(user=user)),
            Entry("b", good, AccessTokenFactory(user=user)),
        ]
    )
    run(pool.graphql, "query { x }")
    assert [e.label for e in pool.entries] == ["b"]
    only_bad = TokenPool(
        [Entry("a", Counting("bad", fail=TokenError("revoked")), AccessTokenFactory(user=user))]
    )
    with pytest.raises(TokenError):
        run(only_bad.graphql, "query { x }")


def test_no_token_left_tells_when_to_try_again(user):  # noqa: F811
    """No token left tells when to try again."""
    reset = timezone.now() + timedelta(minutes=10)
    pool = TokenPool(
        [Entry("a", Counting("a", fail=RateLimited("x", reset)), AccessTokenFactory(user=user))]
    )
    with pytest.raises(NoTokenLeft) as error:
        run(pool.graphql, "query { x }")
    assert error.value.reset_at == reset


def test_point_limit_of_a_fetch(user):  # noqa: F811
    """Point limit of a fetch."""
    pool = TokenPool([Entry("a", Counting("a"), AccessTokenFactory(user=user))], point_limit=1)
    run(pool.graphql, "query { x }")
    with pytest.raises(LimitReached):
        run(pool.graphql, "query { x }")


def test_no_tokens_at_all():
    """No tokens at all."""
    with pytest.raises(TokenError):
        TokenPool([])


def test_expired_stored_token_is_skipped(world):  # noqa: F811
    """Expired stored token is skipped."""
    from datetime import timedelta

    from django.utils import timezone

    from community_insights.tokens import Entry, TokenPool

    from ..fakes import FakeClient

    old = AccessToken.objects.get()
    old.expires_at = timezone.now() - timedelta(days=1)
    old.save()
    good = FakeClient()
    pool = TokenPool([Entry("old", FakeClient(), old), Entry("new", good)])
    run(pool.graphql, "query { x }")
    assert good.requests == 1
    old.refresh_from_db()
    assert old.last_error_code == "ExpiredAPIToken"
    with pytest.raises(errors.ExpiredAPIToken):
        run(TokenPool([Entry("old", FakeClient(), old)]).graphql, "query { x }")
