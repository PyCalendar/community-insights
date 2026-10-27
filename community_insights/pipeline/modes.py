"""Where the fetch worker runs: the modes of FETCH_WORKER."""

from django.conf import settings

from ..errors import UnknownWorkerMode

INTERNAL = "internal"
HTTP_CONTAINER = "external-http-container"
SEPARATE_CONTAINER = "external-separate-container"
INLINE = "inline"

MODES = {
    INTERNAL: "a thread of the web process; the default for development (make run)",
    HTTP_CONTAINER: "a process of its own in the web container; the default of the image",
    SEPARATE_CONTAINER: (
        "only the worker service of docker-compose.yml; the web container runs none"
    ),
    INLINE: "in the request that queued the fetch; for the tests",
}


def mode() -> str:
    """The mode of FETCH_WORKER.

    Returns:
        One of MODES.

    Raises:
        UnknownWorkerMode: If FETCH_WORKER is set to something else.
    """
    found = getattr(settings, "FETCH_WORKER", INTERNAL)
    if found not in MODES:
        raise UnknownWorkerMode(f"FETCH_WORKER={found!r}; use one of: {', '.join(MODES)}.")
    return found
