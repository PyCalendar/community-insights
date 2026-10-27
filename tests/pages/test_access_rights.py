"""Nobody sees the projects of others."""

import pytest
from django.contrib.auth import get_user_model

from community_insights.models import (
    FetchJob,
    Project,
)

pytestmark = pytest.mark.django_db


def test_other_users_projects_are_not_visible(synced, signed_in):
    other = get_user_model().objects.create_user("mallory")
    signed_in.force_login(other)
    assert signed_in.get(f"/s/{Project.objects.get().pk}/").status_code == 404


@pytest.mark.parametrize("scope", ["abc", "1-x", "999", "-", ""])
def test_unknown_scopes_are_404(world, signed_in, scope):  # noqa: F811
    assert signed_in.get(f"/s/{scope}/").status_code == 404


def test_other_users_see_nothing(world, client):  # noqa: F811
    mallory = get_user_model().objects.create_user("mallory", "m@example.org", "pw")
    client.force_login(mallory)
    pk = world["project"].pk
    for url in [f"/s/{pk}/", f"/s/{pk}/data/items.csv", f"/s/{pk}/chart/hours.svg?login=bob"]:
        assert client.get(url).status_code == 404, url
    assert client.post(f"/projects/{pk}/delete/").status_code == 404
    job = FetchJob.objects.filter(user=world["user"]).first()
    assert (
        client.post("/dashboard/downloads/", {"id": job.pk, "action": "cancel"}).status_code == 404
    )


def test_scope_mixing_own_and_foreign_projects_shows_only_own(world, signed_in):  # noqa: F811
    other = get_user_model().objects.create_user("o", "o@example.org", "pw")
    foreign = Project.objects.create(user=other, target="x/y")
    response = signed_in.get(f"/s/{world['project'].pk}-{foreign.pk}/")
    assert response.status_code == 200 and b"x/y" not in response.content
