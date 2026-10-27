"""Visitors without an account may add and read only some repositories per address and hour."""

import pytest
from django.core.cache import cache
from django.test import RequestFactory

from community_insights.models import FetchJob, Repository
from community_insights.visitor_limit import client_address

from ..fakes import FakeClient, item, repo

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _limits(settings):
    """Small limits for visitors, an empty cache, and one trusted proxy."""
    cache.clear()
    settings.VISITOR_SUBMITS_PER_HOUR = 2
    settings.VISITOR_FETCHES_PER_HOUR = 1
    settings.TRUSTED_PROXIES = 1
    yield
    cache.clear()


@pytest.fixture
def github(monkeypatch):
    """A fake GitHub with three repositories."""
    fake = FakeClient(
        repositories=[repo("new/a"), repo("new/b"), repo("new/c")],
        issues=[item(1, "a", "2026-01-01T00:00:00Z")],
    )
    monkeypatch.setattr("community_insights.github.Client", lambda token: fake)
    return fake


def submit(client, target, address="203.0.113.1"):
    """Submit a repository from an address."""
    return client.post(
        "/explore/submit/", {"target": target}, follow=True, HTTP_X_FORWARDED_FOR=address
    )


def test_a_visitor_adds_only_some_repositories_per_hour(world, client, github):
    """A visitor adds only some repositories per hour."""
    submit(client, "new/a")
    submit(client, "new/b")
    refused = submit(client, "new/c")
    assert b"Too many requests from this address" in refused.content
    assert not Repository.objects.filter(full_name="new/c").exists()
    submit(client, "new/c", address="203.0.113.2")
    assert Repository.objects.filter(full_name="new/c").exists(), "another address"


def test_people_with_an_account_have_no_limit(world, signed_in, github):
    """People with an account have no limit."""
    for name in ("new/a", "new/b", "new/c"):
        submit(signed_in, name)
    assert Repository.objects.filter(full_name__startswith="new/").count() == 3


def test_a_visitor_reads_only_some_repositories_per_hour(world, client, github):
    """A visitor reads only some repositories per hour."""
    address = {"HTTP_X_FORWARDED_FOR": "198.51.100.7"}
    client.post("/s/o~empty/fetch/", {"next": "/s/o~empty/"}, **address)
    assert FetchJob.objects.filter(user=None).count() == 1
    refused = client.post("/s/o~empty/fetch/", {"next": "/s/o~empty/"}, follow=True, **address)
    assert b"Too many requests from this address" in refused.content
    assert FetchJob.objects.filter(user=None).count() == 1


def test_no_limit_with_zero(world, client, github, settings):
    """No limit with zero."""
    settings.VISITOR_SUBMITS_PER_HOUR = 0
    for name in ("new/a", "new/b", "new/c"):
        submit(client, name)
    assert Repository.objects.filter(full_name__startswith="new/").count() == 3


@pytest.mark.parametrize(
    ("forwarded", "proxies", "address"),
    [
        ("", 0, "10.0.0.1"),
        ("", 1, "10.0.0.1"),
        ("203.0.113.1", 1, "203.0.113.1"),
        ("6.6.6.6, 203.0.113.1", 1, "203.0.113.1"),  # the first one can be made up
        ("6.6.6.6, 203.0.113.1, 10.1.1.1", 2, "203.0.113.1"),  # behind a TLS proxy
        (" , 203.0.113.1", 1, "203.0.113.1"),
    ],
)
def test_the_address_of_the_visitor(forwarded, proxies, address):
    """The address of the visitor."""
    request = RequestFactory().get("/", REMOTE_ADDR="10.0.0.1", HTTP_X_FORWARDED_FOR=forwarded)
    assert client_address(request, proxies) == address
