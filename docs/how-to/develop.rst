==========================
Set up for development
==========================

You need `uv <https://docs.astral.sh/uv/>`_ and git; uv installs Python 3.13 or newer.

#. Get the code and the environment:

   .. code-block:: bash

       git clone https://github.com/PyCalendar/community-insights.git
       cd community-insights
       make init

   ``make init`` creates ``.venv``, installs the dependencies with the test tools and installs the pre-commit hooks.

#. Create the :doc:`OAuth app <github-oauth>` with the callback ``http://localhost:5000/accounts/github/login/callback/`` and export its values:

   .. code-block:: bash

       export GITHUB_CLIENT_ID=...
       export GITHUB_SECRET=...

#. Start the server; fetches run in a thread of it (``FETCH_WORKER=internal``, see :ref:`worker-modes`). It creates ``data/db.sqlite3`` and the superuser ``admin`` with the password ``admin`` first (``PRODUCTION=false``):

   .. code-block:: bash

       make run

   Open http://localhost:5000 and sign in as ``admin@example.org`` / ``admin``, or at http://localhost:5000/admin/ as ``admin``. ``make docker-run`` builds and runs the container with the same database in ``./data``, so you can switch between both.

   Without an OAuth app you sign up with email and add a token; see the :doc:`../tutorial`.

#. Run the tests and the style check:

   .. code-block:: bash

       make test          # Python, with pytest
       make test-performance  # how fast, with much data and with GitHub
       make test-js       # the JavaScript of the website, with node
       make test-browser  # the website in Firefox, with behave
       WINDOW=375x812 make test-browser   # the same at the size of a phone
       make lint          # the style and the docstrings, with ruff
       make typecheck     # the type hints, with pyright

No test uses the network or a token: GitHub is replaced by a fake (``tests/fakes/``) and the network is blocked in ``tests/conftest.py``. ``tests/pages/test_crawl.py`` visits every page reachable from the start with the test data and checks every link, image and script.

The browser tests are in ``features/``, written like the ones of `Open Web Calendar <https://open-web-calendar.quelltext.eu/>`_. They need Firefox; ``-D headless=false`` shows the browser, ``-D timezone=America/New_York`` changes its time zone:

.. code-block:: bash

    uv run python manage.py behave -D headless=false

The JavaScript is in ``static/js/``; each file works in the browser and in node, its tests are in ``tests/js/``.

``make test-performance`` measures the statistics with 5000 made up items and reads a public repository from GitHub with ``$GITHUB_TOKEN`` (or the token of ``~/.config/community-insights/config.yaml``), twice, to see that the second read asks almost nothing. If the token has few points left, it waits 10 minutes and looks again. ``PERFORMANCE_REPOSITORY`` chooses another repository.

Documentation
=============

The documentation is in ``docs/``, written in reStructuredText and built with Sphinx. The CI runs each check with the same command:

.. code-block:: bash

    make livehtml      # show the documentation while editing it, rebuilt on every change
    make docs          # build it; warnings and references that do not resolve fail
    make linkcheck     # check that its links work; needs the internet
    make vale          # check the prose with Vale; errors fail, suggestions are shown

``make vale`` installs Vale with uvx; nothing else is needed. Words of the project that Vale does not know, such as names of tools, go into ``docs/.vale/styles/config/vocabularies/Base/accept.txt``. Write examples that people type, such as a location, as literals, such as ``Berlin, Germany``, so that their punctuation stays as it is. ``make linkcheck`` skips the files of this repository on GitHub, because a new file is there only after its pull request is merged.

Changes of the database
=======================

A change of a model needs a new migration: ``uv run python manage.py makemigrations``. Never change a migration that may already be applied somewhere, also not ``0001_initial``. A database that applied the earlier version keeps its old tables, and the site then fails with errors such as ``no such column``. ``make test`` checks that no migration is missing.

Structure of the code
=====================

Each module has at most one class; a module that would need more becomes a package, such as ``community_insights/models/`` or ``community_insights/sync/``. The errors are the exception: they are grouped by topic in ``community_insights/errors/``. ``tests/quality/test_structure.py`` checks this.

The type hints are checked with pyright and ``django-types`` (`on GitHub <https://github.com/sbdchd/django-types>`_, ``make typecheck``). When pyright reports an error, first look at what it says about the code: a value that can be ``None`` where it is used as if it never is, or an object reached through too many others. Ignore an error only where the type hints of a library are wrong, with the reason next to it, such as ``# pyright: ignore[reportArgumentType]``. Keep classes small and reusable: the reads of ``community_insights/github/reads.py`` work with any async ``graphql`` function, so the client and the token pool share them.

Build the documentation
=======================

.. code-block:: bash

    uv run --extra docs sphinx-autobuild docs docs/_build/html

Useful commands
===============

``make`` lists all targets. ``uv run python manage.py createsuperuser`` creates an administrator for ``/admin/``; ``uv run python manage.py clear_cache --days 30 --dry-run`` shows what the cache clean-up would delete.
