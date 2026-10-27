"""The projects of an account may hold some pull requests and issues; administrators no limit."""

import pytest

from community_insights import user_limit
from community_insights.errors import UserItemsLimitReached
from community_insights.models import FetchJob

from ..fakes import FakeClient, item

pytestmark = pytest.mark.django_db


def test_the_items_of_the_projects_are_counted(synced, user):
    """The items of the repositories of the projects count once."""
    assert user_limit.items_of(user) == 3


def test_a_fetch_over_the_limit_is_refused(world, signed_in, settings, monkeypatch):
    """A fetch that would add more items than allowed is refused with what to do."""
    settings.USER_MAX_ITEMS = 6
    big = FakeClient(issues=[item(i, "a", "2026-01-01T00:00:00Z") for i in range(1, 40)])
    monkeypatch.setattr("community_insights.github.Client", lambda token: big)
    pk = world["empty"].pk
    page = signed_in.get(f"/s/{pk}/fetch/").content.decode()
    assert "Your projects hold 5 of 6 pull requests and issues" in page
    response = signed_in.post(f"/s/{pk}/fetch/", {"next": f"/s/{pk}/"}, follow=True)
    assert b"Too many pull requests and issues for your account" in response.content
    assert not FetchJob.objects.filter(repository__full_name="o/empty", status="done").exists()


def test_administrators_and_zero_have_no_limit(user, settings):
    """Administrators have no limit, and 0 turns it off."""
    settings.USER_MAX_ITEMS = 1
    with pytest.raises(UserItemsLimitReached, match="1 are allowed"):
        user_limit.check(user, 5)
    user.is_staff = True
    assert user_limit.limit_of(user) is None
    user_limit.check(user, 5)
    user.is_staff = False
    settings.USER_MAX_ITEMS = 0
    assert user_limit.limit_of(user) is None
    user_limit.check(user, 10**9)


def test_a_fetch_within_the_limit_runs(world, signed_in, monkeypatch):
    """A fetch within the limit runs as before."""
    monkeypatch.setattr("community_insights.github.Client", lambda token: FakeClient())
    pk = world["empty"].pk
    signed_in.post(f"/s/{pk}/fetch/", {"next": f"/s/{pk}/"})
    assert FetchJob.objects.filter(repository__full_name="o/empty", status="done").exists()
