"""Run manage.py fetch_worker --once with one job in a fresh process and print what it imported.

tests/fetching/test_worker_imports.py starts this module with ``python -m``, in a process of
its own, like the image starts the fetch worker: the modules the tests imported before cannot
hide the modules the worker imports. GitHub is the fake of the tests; the network is not used.

The output is JSON: the status of the job, its message, and the names of the top level modules
the process imported, without the standard library and the fakes of the tests (``tests`` and
the ``respx`` they import), and the modules of ``community_insights`` it imported.
"""

import io
import json
import os
import sys

# Loaded for the fakes of the tests, not by the worker.
TESTS = {"__main__", "__mp_main__", "tests", "respx"}


def top_level_modules() -> list[str]:
    """The top level modules imported so far, without the standard library and the tests.

    Names that start with ``_``, and ``cython_runtime``, are the compiled parts of the packages
    that import them, such as ``_cffi_backend`` of ``cryptography``, and are left out too.

    Returns:
        The sorted names, such as ``django`` for ``django.db.models``.
    """
    names = {name.partition(".")[0] for name in sys.modules}
    names -= set(sys.stdlib_module_names) | TESTS | {"cython_runtime"}
    return sorted(name for name in names if not name.startswith("_"))


def own_modules() -> list[str]:
    """The modules of the site the process imported.

    Returns:
        The sorted names, such as ``community_insights.pipeline.worker``.
    """
    return sorted(name for name in sys.modules if name.partition(".")[0] == "community_insights")


def main() -> None:
    """Prepare a database with one queued job, run the fetch worker once and print the result."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "community_insights.settings")
    import django

    django.setup()
    from django.contrib.auth import get_user_model
    from django.core.management import call_command

    from community_insights import github
    from community_insights.models import AccessToken, FetchJob
    from community_insights.sync import store_repository
    from tests.fakes.builders import item, node, repo
    from tests.fakes.client import FakeClient

    call_command("migrate", verbosity=0)
    user = get_user_model().objects.create_user("worker", "worker@example.com", "password")
    AccessToken.objects.create(user=user, token="token", login="worker")
    repository = store_repository(repo("o/r"))
    job = FetchJob.objects.create(user=user, repository=repository, items_expected=1)
    answer = node("maint", "2026-01-05T12:00:00Z", "MEMBER")
    client = FakeClient(prs=[item(1, "bob", "2026-01-05T10:00:00Z", comments=[answer], reviews=[])])
    github.Client = lambda token, *args, **kwargs: client  # the worker reads the fake GitHub

    call_command("fetch_worker", "--once", stdout=io.StringIO())
    job.refresh_from_db()
    result = {"status": job.status, "message": job.message}
    print(json.dumps(result | {"modules": top_level_modules(), "own": own_modules()}))


if __name__ == "__main__":
    main()
