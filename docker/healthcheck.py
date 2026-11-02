"""The health check of the container: GET /health/ of the site in this container.

Django answers 400 to a host that is not in ALLOWED_HOSTS, also to 127.0.0.1, so
the check sends the first host the site allows.
"""

import os
import sys
import urllib.request

LOCAL = "127.0.0.1"


def allowed_host(allowed_hosts: str) -> str:
    """The first host name of ALLOWED_HOSTS, to send as Host.

    Args:
        allowed_hosts: The value of ALLOWED_HOSTS, comma separated.

    Returns:
        The host; for ``*`` or nothing, 127.0.0.1.

    Examples:
        >>> allowed_host("insight.pycal.org,www.insight.pycal.org")
        'insight.pycal.org'
        >>> allowed_host(".pycal.org")
        'pycal.org'
        >>> allowed_host("*")
        '127.0.0.1'
    """
    for host in allowed_hosts.split(","):
        host = host.strip().lstrip(".")
        if host and "*" not in host:
            return host
    return LOCAL


def check(port: str, allowed_hosts: str, timeout: float = 25) -> bool:
    """Whether the site in this container answers its health check.

    Args:
        port: The port of nginx in the container.
        allowed_hosts: The value of ALLOWED_HOSTS.
        timeout: Seconds to wait for the answer.

    Returns:
        True if the database and the cache work.
    """
    request = urllib.request.Request(
        f"http://{LOCAL}:{port}/health/",
        headers={"Host": allowed_host(allowed_hosts), "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status == 200
    except OSError as error:  # also HTTPError: 400 for a host, 500 for a broken check
        print(f"unhealthy: {error}", file=sys.stderr)
        return False


if __name__ == "__main__":
    sys.exit(0 if check(os.environ["PORT"], os.environ.get("ALLOWED_HOSTS", "")) else 1)
