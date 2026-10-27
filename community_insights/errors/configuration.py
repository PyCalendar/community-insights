"""Errors in the configuration of the site."""

from django.utils.translation import gettext_lazy as _

from .base import CommunityError


class ConfigurationError(CommunityError):
    """A setting of the site cannot be used.

    The message names the setting. See *Configuration* in the reference of the
    documentation for the values it takes.
    """

    title = _("Invalid configuration")


class UnknownWorkerMode(ConfigurationError):
    """FETCH_WORKER has a value that is no mode of the fetch worker.

    Use ``internal`` (a thread of the web process, for development),
    ``external-http-container`` (a process in the web container, the default of
    the image) or ``external-separate-container`` (the worker service of
    docker-compose.yml).
    """

    title = _("Unknown mode of the fetch worker")
