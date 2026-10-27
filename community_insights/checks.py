"""Checks of the configuration, run by manage.py before the site starts."""

from django.core import checks

from .errors import UnknownWorkerMode


@checks.register()
def fetch_worker_mode(app_configs=None, **kwargs) -> list[checks.Error]:
    """FETCH_WORKER is one of the modes.

    Returns:
        An error that says the modes, or nothing.
    """
    from .pipeline import modes

    try:
        modes.mode()
    except UnknownWorkerMode as error:
        return [checks.Error(str(error), hint=error.docs_url(), id="community.E001")]
    return []
