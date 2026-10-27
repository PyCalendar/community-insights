"""Badges of the response times."""

import pytest

from community_insights.models import Project

pytestmark = pytest.mark.django_db


def test_badge_is_public_and_configurable(synced, client):
    token = Project.objects.get().badge_token
    response = client.get(f"/badge/{token}.svg?kind=pr&percentile=95&class=bot")
    assert response.status_code == 200
    assert b"PR response p95 (bot)" in response.content and b"10min" in response.content
    assert b"no data" in client.get(f"/badge/{token}.svg?kind=issue&class=bot").content
    assert client.get(f"/badge/{token}.svg?class=nobody").status_code == 404
    assert client.get("/badge/wrong.svg").status_code == 404


def test_badge_without_data_and_with_bad_parameters(world, client):  # noqa: F811
    token = world["empty"].badge_token
    assert b"no data" in client.get(f"/badge/{token}.svg").content
    for query in ["percentile=abc", "percentile=500", "percentile=-1", "kind=nonsense"]:
        assert client.get(f"/badge/{token}.svg?{query}").status_code == 200, query
    assert b"p100" in client.get(f"/badge/{token}.svg?percentile=500").content
