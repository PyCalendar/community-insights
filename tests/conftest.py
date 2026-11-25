import socket

import pytest
from django.utils import translation

from .data import replied, signed_in, synced, user, world  # noqa: F401  (shared fixtures)


@pytest.fixture
def client():
    """The client of the tests: pages of public projects open at their public address.

    Returns:
        A ``tests.fakes.scope_client.ScopeClient``.
    """
    from .fakes.scope_client import ScopeClient

    return ScopeClient()


@pytest.fixture(autouse=True)
def _settings(settings, tmp_path):
    """The settings of all tests: work in the request, files in a temporary folder."""
    settings.FETCH_WORKER = "inline"  # fetches and documents run in the request
    settings.DATA_DIR = tmp_path  # the documents made
    settings.NOMINATIM_URL = ""  # places are found offline; tests of Nominatim fake it
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
        """Fail: the tests do not use the network."""
        raise AssertionError("the tests must not use the network")

    monkeypatch.setattr(socket.socket, "connect", refuse)
