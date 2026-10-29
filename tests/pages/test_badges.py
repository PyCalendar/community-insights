"""Badges of the response times."""

import pytest

from community_insights.models import Project

pytestmark = pytest.mark.django_db


def test_badge_is_public_and_configurable(synced, client):
    """Badge is public and configurable."""
    token = Project.objects.get().badge_token
    response = client.get(f"/badge/{token}.svg?kind=pr&percentile=95&class=bot")
    assert response.status_code == 200
    assert b"PR response p95 (bot)" in response.content and b"10min" in response.content
    assert b"no data" in client.get(f"/badge/{token}.svg?kind=issue&class=bot").content
    assert client.get(f"/badge/{token}.svg?class=nobody").status_code == 404
    assert client.get("/badge/wrong.svg").status_code == 404


def test_badge_without_data_and_with_bad_parameters(world, client):  # noqa: F811
    """Badge without data and with bad parameters."""
    token = world["empty"].badge_token
    assert b"no data" in client.get(f"/badge/{token}.svg").content
    for query in ["percentile=abc", "percentile=500", "percentile=-1", "kind=nonsense"]:
        assert client.get(f"/badge/{token}.svg?{query}").status_code == 200, query
    assert b"p100" in client.get(f"/badge/{token}.svg?percentile=500").content


def test_the_left_side_can_be_chosen(synced, client):
    """The left side can be chosen."""
    token = Project.objects.get().badge_token
    content = client.get(f"/badge/{token}.svg?percentile=95&label=time+to+answer").content
    assert b"time to answer" in content and b"PR response" not in content
    spaces = client.get(f"/badge/{token}.svg?label=%20%20a%0A%20b%20").content
    assert b">a b<" in spaces, "spaces are made one"
    long = client.get(f"/badge/{token}.svg?label=" + "x" * 100).content
    assert b"x" * 60 in long and b"x" * 61 not in long
    assert b"PR response" in client.get(f"/badge/{token}.svg?label=%20").content


def test_the_left_side_is_escaped(synced, client):
    """The left side is escaped."""
    token = Project.objects.get().badge_token
    content = client.get(f"/badge/{token}.svg?label=%3Cscript%3E").content
    assert b"<script>" not in content and b"&lt;script&gt;" in content


def test_the_overview_builds_the_badge_with_all_formats(synced, signed_in):
    """The overview builds the badge with all formats."""
    pk = Project.objects.get().pk
    page = signed_in.get(f"/s/{pk}/").content.decode()
    assert 'data-badge="label"' in page
    for name in ("markdown", "rst", "html", "link"):
        assert f'data-copy="#badge-{name}"' in page
    assert 'data-share-link="http://testserver/s/o~r/"' in page, "opens without a sign in"
    assert page.index("js/share.js") < page.index("js/badge.js"), "badge.js uses share.js"


def test_the_badge_uses_the_chosen_model(synced, client):
    """The badge uses the chosen model."""
    token = Project.objects.get().badge_token
    measured = client.get(f"/badge/{token}.svg?percentile=50&class=bot").content
    assert b"PR response p50 (bot)" in measured and b"10min" in measured
    for model in ("normal", "exponential", "kaplan-meier"):
        content = client.get(f"/badge/{token}.svg?percentile=50&class=bot&model={model}").content
        assert f"PR response p50 (bot, {model})".encode() in content, model
    explicit = client.get(f"/badge/{token}.svg?percentile=50&class=bot&model=measured").content
    assert explicit == measured


def test_kaplan_meier_says_when_a_share_is_never_reached(synced, client):
    """Kaplan meier says when a share is never reached."""
    token = Project.objects.get().badge_token
    content = client.get(f"/badge/{token}.svg?percentile=99&class=bot&model=kaplan-meier").content
    assert b"not reached" in content, "1 of 2 pull requests got no response of a bot"
    assert b"no data" in client.get(f"/badge/{token}.svg?kind=issue&class=bot").content


def test_unknown_models_and_odd_percentiles(synced, client):
    """Unknown models and odd percentiles."""
    token = Project.objects.get().badge_token
    assert client.get(f"/badge/{token}.svg?model=guess").status_code == 404
    for value in ("nan", "inf", "-inf", "1e400"):
        assert client.get(f"/badge/{token}.svg?percentile={value}").status_code == 200, value
    assert b"p50" in client.get(f"/badge/{token}.svg?percentile=nan").content
