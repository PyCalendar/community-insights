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

#. Optional: to sign in with GitHub, create the :doc:`OAuth app <github-oauth>` with the callback ``http://localhost:5000/accounts/github/login/callback/`` and export its values. Without it, sign up with email and add a :doc:`token <tokens>`.

   .. code-block:: bash

       export GITHUB_CLIENT_ID=...
       export GITHUB_SECRET=...

#. Start the server; fetches run in a thread of it (``FETCH_WORKER=internal``, see :ref:`worker-modes`). It creates ``data/db.sqlite3``, the superuser ``admin@example.com`` with the password ``admin`` and the demo project (``PRODUCTION=false``):

   .. code-block:: bash

       make run

#. Open http://localhost:5000 and sign in as ``admin@example.com`` with the password ``admin``, also at http://localhost:5000/admin/. ``make docker-run`` builds and runs the container with the same database in ``./data``, so you can switch between both.


.. _run-the-tests:

Run the tests
=============

Run what the CI runs, with the same commands:

.. code-block:: bash

    make test               # Python, with pytest and coverage
    make test-js            # the JavaScript, with node and jsdom
    make test-browser       # the website in Firefox, with Playwright
    WINDOW=375x812 make test-browser   # the same at the size of a phone
    make lint               # the style and the docstrings, with ruff
    make typecheck          # the type hints, with pyright
    make check-graphql      # the GraphQL queries against the schema of GitHub
    make check-site-links   # every link of the running site, with LinkChecker
    make check-vendor       # static/vendor is what make vendor makes
    make test-all           # all of them and the checks of the documentation

No test uses the network or a token: GitHub is replaced by a fake (``tests/fakes/``) and the network is blocked in ``tests/conftest.py``. Put a new test into the folder of ``tests/`` of its topic.

Write a test
------------

- Make the rows a test needs with the factories of ``factory_boy`` in ``tests/factories/``. They fill every field the test does not name: ``FetchJobFactory(status=FetchJob.RUNNING)``.
- Test the GitHub clients by giving them a ``transport`` of ``respx``, which answers as GitHub would: ``answering`` in ``tests/fakes/session.py`` does this.
- Test the JavaScript in ``tests/js/`` with pages of ``jsdom``. Pass a library of the browser, such as Sortable.js, to ``setup``, so a test can pass a fake that records how it was called.
- Test what people do in the browser in ``tests/browser/``: ``Site`` in ``tests/browser/site.py`` opens pages, clicks and checks the page; Playwright waits for each element.

Watch the browser tests
-----------------------

``make test`` leaves out the browser tests (the marker ``browser``); ``make browsers`` installs the Firefox of Playwright. Show the browser, or change its time zone:

.. code-block:: bash

    make test-browser BROWSER_FLAGS=--headed
    TIME_ZONE=America/New_York make test-browser

Check the links and the queries
-------------------------------

- ``make check-site-links`` starts the site on a new database in ``.cache/site`` with ``admin@example.com`` and the demo project, and lets `LinkChecker <https://linkchecker.github.io/linkchecker/>`_ follow every link, signed in. ``tests/linkchecker/linkcheckerrc`` leaves out the links that only sort, share or sign out.
- ``make check-graphql`` downloads the schema GitHub publishes and validates every query with ``gql``. A new query goes into ``community_insights/github/catalog.py``, so that it is checked, too.
- ``tests/pages/test_crawl.py`` visits every page with the test data and checks every link, image and script, without a server.

Measure the speed
-----------------

``make test-performance`` measures the statistics with 5000 made up items and reads a public repository from GitHub with ``$GITHUB_TOKEN`` (or the token of ``~/.config/community-insights/config.yaml``), twice, to see that the second read asks almost nothing. If the token has few points left, it waits 10 minutes and looks again. ``PERFORMANCE_REPOSITORY`` chooses another repository.

Check the documentation
=======================

The documentation is in ``docs/``, written in reStructuredText and built with Sphinx. The CI runs each check with the same command:

.. code-block:: bash

    make livehtml      # show the documentation while editing it, rebuilt on every change
    make docs          # build it; warnings and references that do not resolve fail
    make linkcheck     # check that its links work; needs the internet
    make vale          # check the prose with Vale; errors fail, suggestions are shown

``make vale`` installs Vale with uvx; nothing else is needed. Words of the project that Vale does not know, such as names of tools, go into ``docs/.vale/styles/config/vocabularies/Base/accept.txt``. Write examples that people type, such as a location, as literals, such as ``Berlin, Germany``, so that their punctuation stays as it is. ``make linkcheck`` skips the files of this repository on GitHub, because a new file is there only after its pull request is merged. A server that the machine cannot reach at all (``Network is unreachable``, such as an IPv6 address on a runner without IPv6) is listed, but does not fail the check; ``tests/linkchecker/docs.py`` decides this from ``docs/_build/linkcheck/output.json``.

Update the JavaScript and CSS of other projects
===============================================

The pages load Bootstrap and other libraries from ``static/vendor/``, never from other servers. Their versions are in ``package.json`` and ``package-lock.json``; ``make vendor`` installs them with ``npm ci`` and copies the files the pages need, without their source maps. To update one, change its version with ``npm install --save-exact NAME@VERSION``, run ``make vendor``, and update ``static/vendor/vendor.json`` and ``REUSE.toml``.

``make check-vendor`` copies them again into ``.cache/vendor`` and compares: the CI fails when ``static/vendor`` is not what ``make vendor`` makes.

Change the database
===================

A change of a model needs a new migration: ``uv run python manage.py makemigrations``. Never change a migration that may already be applied somewhere, also not ``0001_initial``. A database that applied the earlier version keeps its old tables, and the site then fails with errors such as ``no such column``. ``make test`` checks that no migration is missing.

Write code
==========

- Put at most one class into a module; a module that would need more becomes a package, such as ``community_insights/models/``. The errors are the exception: they are grouped by topic in ``community_insights/errors/``. ``tests/quality/test_structure.py`` checks this.
- When pyright (``make typecheck``, with ``django-types``) reports an error, first look at what it says about the code: a value that can be ``None`` where it is used as if it never is, or an object reached through too many others. Ignore an error only where the type hints of a library are wrong, with the reason next to it, such as ``# pyright: ignore[reportArgumentType]``.
- Draw a new chart twice: as SVG in ``community_insights/charts.py`` and, with the same name and arguments, as data for Chart.js in ``community_insights/chart_data.py``; add its name to ``INTERACTIVE``.
- For a part of a page that changes while it is open, render it with Django and let htmx fetch it with ``hx-`` attributes; answer ``request.htmx`` with that part only.

:doc:`../explanation/design` explains why the site is built like this.

Other commands
==============

``make`` lists all targets. ``uv run python manage.py createsuperuser`` creates an administrator for ``/admin/``; ``uv run python manage.py clear_cache --days 30 --dry-run`` shows what the cache clean-up would delete.
