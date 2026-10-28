"""Checks of the configuration, run by manage.py before the site starts."""

from django.conf import settings
from django.core import checks

from .errors import EmailEncryptionConflict, UnknownWorkerMode


@checks.register()
def fetch_worker_mode(app_configs=None, **kwargs) -> list[checks.Error]:
    """FETCH_WORKER is one of the modes.

    Returns:
        An error that says the modes, or nothing.

    Args:
        app_configs: The apps to check, as Django gives them.
        **kwargs: More arguments of Django.
    """
    from .pipeline import modes

    try:
        modes.mode()
    except UnknownWorkerMode as error:
        return [checks.Error(str(error), hint=error.docs_url(), id="community.E001")]
    return []


@checks.register()
def mail_encryption(app_configs=None, **kwargs) -> list[checks.Error]:
    """EMAIL_USE_SSL and EMAIL_USE_TLS are not both on.

    Args:
        app_configs: The apps to check, as Django gives them.
        **kwargs: More arguments of Django.

    Returns:
        An error that says which to keep, or nothing.
    """
    if settings.EMAIL_USE_SSL and settings.EMAIL_USE_TLS:
        error = EmailEncryptionConflict(
            "EMAIL_USE_SSL and EMAIL_USE_TLS are both true; set only one: EMAIL_USE_SSL for "
            f"port 465, EMAIL_USE_TLS for port 587 (EMAIL_PORT={settings.EMAIL_PORT})."
        )
        return [checks.Error(str(error), hint=error.docs_url(), id="community.E002")]
    return []
