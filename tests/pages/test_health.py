"""The health check of the container."""

import pytest

pytestmark = pytest.mark.django_db


def test_health_endpoint(client, db):
    """Health endpoint."""
    response = client.get("/health/", HTTP_ACCEPT="application/json")
    assert response.status_code == 200


def healthcheck():
    """The script of the HEALTHCHECK of the image, docker/healthcheck.py.

    Returns:
        The module.
    """
    import importlib.util
    from pathlib import Path

    path = Path(__file__).parents[2] / "docker" / "healthcheck.py"
    spec = importlib.util.spec_from_file_location("healthcheck", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("allowed", "host"),
    [
        ("insight.pycal.org", "insight.pycal.org"),
        (" insight.pycal.org , localhost", "insight.pycal.org"),
        (".pycal.org", "pycal.org"),
        ("*", "127.0.0.1"),
        ("*,example.org", "example.org"),
        ("", "127.0.0.1"),
    ],
)
def test_the_health_check_sends_a_host_the_site_allows(allowed, host):
    """The host is the first of ALLOWED_HOSTS that names a host."""
    assert healthcheck().allowed_host(allowed) == host


@pytest.mark.parametrize("allowed", ["insight.pycal.org", ".pycal.org", "*"])
def test_the_site_answers_the_host_of_the_health_check(client, settings, allowed):
    """Django answers the health check with the host it sends, whatever ALLOWED_HOSTS is."""
    settings.ALLOWED_HOSTS = [allowed]
    host = healthcheck().allowed_host(allowed)
    response = client.get("/health/", HTTP_ACCEPT="application/json", HTTP_HOST=host)
    assert response.status_code == 200


def test_the_address_of_the_container_is_no_allowed_host(client, settings):
    """127.0.0.1 alone was refused with 400 when ALLOWED_HOSTS names the site: unhealthy."""
    settings.ALLOWED_HOSTS = ["insight.pycal.org"]
    response = client.get("/health/", HTTP_HOST="127.0.0.1:5000")
    assert response.status_code == 400


def test_the_health_check_asks_nginx_in_the_container(monkeypatch):
    """The request goes to the port of the container, with the allowed host."""
    module = healthcheck()
    sent = []

    class Answer:
        """An answer of 200."""

        status = 200

        def __enter__(self):
            """The answer.

            Returns:
                Itself.
            """
            return self

        def __exit__(self, *exception):
            """Nothing to close."""

    def urlopen(request, timeout):
        """Remember the request and answer 200."""
        sent.append((request.full_url, request.get_header("Host"), timeout))
        return Answer()

    monkeypatch.setattr(module.urllib.request, "urlopen", urlopen)
    assert module.check("5000", "insight.pycal.org", timeout=7)
    assert sent == [("http://127.0.0.1:5000/health/", "insight.pycal.org", 7)]


def test_an_error_makes_the_container_unhealthy(monkeypatch, capsys):
    """A refused host, a broken check or no answer: the check fails and says why."""
    import urllib.error

    module = healthcheck()

    def refused(request, timeout):
        """Refuse the host, as Django does."""
        raise urllib.error.HTTPError(request.full_url, 400, "Bad Request", {}, None)  # type: ignore[arg-type]

    monkeypatch.setattr(module.urllib.request, "urlopen", refused)
    assert not module.check("5000", "insight.pycal.org")
    assert "400" in capsys.readouterr().err

    def silent(request, timeout):
        """Answer nothing in time."""
        raise TimeoutError("timed out")

    monkeypatch.setattr(module.urllib.request, "urlopen", silent)
    assert not module.check("5000", "")


def test_the_image_uses_the_health_check_script():
    """The Dockerfile copies the script and runs it as HEALTHCHECK."""
    from pathlib import Path

    dockerfile = (Path(__file__).parents[2] / "Dockerfile").read_text()
    assert "docker/healthcheck.py" in dockerfile
    assert "CMD python healthcheck.py" in dockerfile


def test_the_health_check_imports_only_the_standard_library():
    """Each check is a process of its own: it loads no Django and no library of the statistics."""
    import json
    import subprocess
    import sys
    from pathlib import Path

    script = Path(__file__).parents[2] / "docker" / "healthcheck.py"
    found = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            "import json, runpy, sys; runpy.run_path(sys.argv[1]);"
            " print(json.dumps(sorted({m.split('.')[0] for m in sys.modules})))",
            str(script),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    modules = set(json.loads(found.stdout))
    outside = {m for m in modules if m not in sys.stdlib_module_names and not m.startswith("_")}
    assert outside == set()
    assert "urllib" in modules


def test_nginx_forwards_with_http_1_1():
    """nginx forwards to gunicorn with HTTP/1.1, as requests come in, not with HTTP/1.0."""
    from pathlib import Path

    config = (Path(__file__).parents[2] / "docker" / "nginx.conf").read_text()
    assert "proxy_http_version 1.1;" in config
    assert 'proxy_set_header Connection "";' in config
