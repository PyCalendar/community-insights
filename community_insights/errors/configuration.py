"""Errors in the configuration of the site."""

from django.utils.translation import gettext_lazy as _

from .base import CommunityError


class ConfigurationError(CommunityError):
    """A setting of the site cannot be used.

    The message names the setting. See :doc:`/reference/configuration` for the values it takes.
    """

    title = _("Invalid configuration")
    guide = "reference/configuration.html"
    guide_title = _("The settings of the site")


class UnknownWorkerMode(ConfigurationError):
    """FETCH_WORKER has a value that is no mode of the fetch worker.

    Use ``internal`` (a thread of the web process, for development),
    ``external-http-container`` (a process in the web container, the default of
    the image) or ``external-separate-container`` (the worker service of
    docker-compose.yml).

    The settings of the site: :doc:`/reference/configuration`.
    """

    title = _("Unknown mode of the fetch worker")
    guide = "reference/configuration.html"
    guide_title = _("The settings of the site")
