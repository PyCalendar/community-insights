import socket

import pytest
from django.utils import translation

from .data import signed_in, synced, user, world  # noqa: F401  (shared fixtures)


@pytest.fixture(autouse=True)
def _settings(settings):
    settings.FETCH_WORKER = "inline"  # fetches run in the request
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }


@pytest.fixture(autouse=True)
def _english():
    """Each test starts in English; a request in German does not change the next test."""
    translation.activate("en")
    yield
    translation.deactivate()


@pytest.fixture(autouse=True)
def _no_network(request, monkeypatch):
    """The tests never reach GitHub: the GitHub client is replaced by a fake or its
    HTTP session is mocked. Only tests marked "network" may use it."""
    if request.node.get_closest_marker("network"):
        return

    def refuse(*args, **kwargs):
        raise AssertionError("the tests must not use the network")

    monkeypatch.setattr(socket.socket, "connect", refuse)
