"""Tokens of the site that everybody can use."""

import pytest
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db


def test_shared_tokens_of_the_site(db, monkeypatch):
    from django.core.management import CommandError, call_command

    from community_insights.models import AccessToken
    from community_insights.tokens import entries_for

    from ..fakes import Answering, FakeClient

    monkeypatch.setattr("community_insights.github.Client", lambda token: Answering(token))
    with pytest.raises(CommandError, match="create the superuser first"):
        call_command("add_shared_token", "root", "t")
    get_user_model().objects.create_user("plain", "p@example.org", "pw")
    with pytest.raises(CommandError, match="no superuser"):
        call_command("add_shared_token", "plain", "t")
    get_user_model().objects.create_superuser("root", "root@example.org", "pw")
    call_command("add_shared_token", "root", "t", "--max-percent", "50")
    shared = AccessToken.objects.get(user__username="root")
    assert (shared.max_points, shared.shared_points, shared.login) == (2500, 2500, "kim")
    somebody = get_user_model().objects.get(username="plain")
    entries = entries_for(somebody, lambda token: FakeClient())
    assert [e.shared for e in entries] == [True], "everybody can use it"
