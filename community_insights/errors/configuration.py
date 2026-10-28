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


class InvalidDefaultSuperuser(ConfigurationError):
    """DEFAULT_SUPERUSER is not an email address and a password.

    Write it as ``email:password``, such as ``admin@example.com:a-long-password``:
    the superuser signs in with the email address. The password is set each time
    the site starts, so changing it here changes the password.

    The settings of the site: :doc:`/reference/configuration`.
    """

    title = _("Invalid superuser")
    guide = "reference/configuration.html"
    guide_title = _("The settings of the site")


class EmailEncryptionConflict(ConfigurationError):
    """EMAIL_USE_SSL and EMAIL_USE_TLS are both on, but a mail server speaks only one.

    Port 465 speaks TLS from the first byte: set ``EMAIL_USE_SSL=true`` or nothing. Port
    587 starts in plain text and switches with STARTTLS: set ``EMAIL_USE_TLS=true`` or
    nothing. Remove the other one from ``.env``.

    The settings of the site: :doc:`/reference/configuration`.
    """

    title = _("Two encryptions for the mail server")
    guide = "reference/configuration.html"
    guide_title = _("The settings of the site")
