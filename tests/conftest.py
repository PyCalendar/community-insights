import socket

import pytest
from django.utils import translation

from .data import signed_in, synced, user, world  # noqa: F401  (shared fixtures)


@pytest.fixture(autouse=True)
def _settings(settings, tmp_path):
    """The settings of all tests: work in the request, files in a temporary folder."""
    settings.FETCH_WORKER = "inline"  # fetches and documents run in the request
    settings.DATA_DIR = tmp_path  # the documents made
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
