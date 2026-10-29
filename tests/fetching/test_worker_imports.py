"""The fetch worker stays small: it imports only the modules listed here.

The image runs ``manage.py fetch_worker`` as a process of its own next to gunicorn, with little
memory for both (see WORKERS in docs/reference/configuration.rst). The libraries of the
statistics (pandas, numpy, matplotlib, lifelines, statsmodels) add about 200 MB to a process;
the worker reads GitHub and needs none of them. A module that is not listed fails the test:
import it where the pages need it, or, if the worker needs it and it is small, list it.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]

# The packages, other than the standard library, the worker may import.
ALLOWED = {
    "aiolimiter",  # the limit of requests to GitHub
    "allauth",  # an app of the settings: the linked GitHub accounts
    "anyio",  # httpx
    "asgiref",  # Django
    "cachalot",  # the cache of the statistics, forgets what a fetch changes
    "certifi",  # httpx, requests
    "charset_normalizer",  # requests
    "click",  # an app of the settings
    "colorama",  # an app of the settings
    "community_insights",
    "cryptography",  # the encrypted tokens
    "django",
    "django_bootstrap5",  # an app of the settings
    "django_filters",  # an app of the settings
    "django_htmx",  # a middleware of the settings
    "django_tables2",  # an app of the settings
    "dns",  # the check of email addresses of allauth
    "encrypted_fields",  # the encrypted tokens
    "environ",  # the settings
    "h11",  # httpx
    "health_check",  # an app of the settings
    "httpcore",  # httpx
    "httpx",  # reads GitHub
    "idna",  # httpx, requests
    "ordered_model",  # the order of the tokens
    "psycopg",  # the database driver of PostgreSQL
    "psycopg_binary",  # psycopg
    "pygments",  # an app of the settings
    "requests",  # an app of the settings
    "sqlparse",  # Django
    "urllib3",  # requests
}

# Never in the worker: the libraries of the statistics and the charts.
BIG = {"pandas", "numpy", "scipy", "matplotlib", "lifelines", "statsmodels", "openpyxl", "PIL"}

# The packages of the site the worker may import: no statistics, charts or pages.
OWN = {
    "community_insights",
    "community_insights.admin",
    "community_insights.apps",
    "community_insights.checks",
    "community_insights.cleanup",
    "community_insights.documents",
    "community_insights.errors",
    "community_insights.github",
    "community_insights.mail_encryption",
    "community_insights.management",
    "community_insights.migrations",
    "community_insights.models",
    "community_insights.pipeline",
    "community_insights.settings",
    "community_insights.sync",
    "community_insights.tokens",
}


@pytest.fixture(scope="module")
def worker(tmp_path_factory):
    """Run the fetch worker with one job in a process of its own, with a new database.

    Returns:
        The JSON the process printed: status and message of the job, and the modules.
    """
    data = tmp_path_factory.mktemp("worker")
    env = os.environ | {
        "DJANGO_SETTINGS_MODULE": "community_insights.settings",
        "DATA_DIR": str(data),
        "DATABASE_URL": f"sqlite:///{data / 'db.sqlite3'}",
        "CACHE_URL": f"filecache://{data / 'cache'}",
        "FETCH_WORKER": "external-http-container",
        "PRODUCTION": "false",
        "DEBUG": "",
    }
    done = subprocess.run(
        [sys.executable, "-m", "tests.fetching.worker_process"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout.splitlines()[-1])


def test_the_worker_fetched_the_job(worker):
    """The worker really read the repository, so its imports during a fetch count too."""
    assert worker["status"] == "done", worker["message"]


def test_the_worker_imports_only_allowed_packages(worker):
    """Each package the worker imports is in the list of allowed ones."""
    assert set(worker["modules"]) - ALLOWED == set()


def test_the_worker_imports_no_big_library(worker):
    """None of the libraries of the statistics is loaded, also not through another one."""
    assert set(worker["modules"]) & BIG == set()


def test_the_big_libraries_are_not_allowed():
    """Nobody can allow a library of the statistics by adding it to the list."""
    assert ALLOWED & BIG == set()


def test_the_worker_imports_only_allowed_parts_of_the_site(worker):
    """The worker imports no statistics, charts or pages of the site."""
    packages = {".".join(name.split(".")[:2]) for name in worker["own"]}
    assert packages - OWN == set()
