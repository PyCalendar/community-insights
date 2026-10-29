=============================
Configuration (environment)
=============================

The application reads its settings from environment variables. With Docker, put them in ``.env`` (see ``.env.example``).

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Variable
     - Default
     - Meaning
   * - ``GITHUB_CLIENT_ID``
     - none
     - Client ID of the :doc:`OAuth app <../how-to/github-oauth>`. Required to sign in.
   * - ``GITHUB_SECRET``
     - none
     - Client secret of the OAuth app. Required to sign in.
   * - ``GITHUB_SCOPE``
     - ``read:user``
     - Comma separated scopes requested at sign in. Private repositories need ``repo``; people can allow it later on *GitHub access*.
   * - ``SECRET_KEY``
     - generated
     - Django secret key. If empty, one is created in ``DATA_DIR/secret_key`` and reused.
   * - ``SALT_KEY``
     - generated
     - Encrypts the GitHub tokens in the database, with ``SECRET_KEY``. If empty, one is created in ``DATA_DIR/salt_key``. Changing either makes the stored tokens unreadable: keep ``./data``.
   * - ``CACHE_URL``
     - files in ``DATA_DIR/cache``
     - The cache of the statistics (``django-cachalot``), shared by all processes, for example ``redis://redis:6379/0``.
   * - ``CACHE_KEEP_DAYS``
     - ``90``
     - Repositories and people nobody looked at for so many days are deleted, once a day; their projects stay and read them again when needed. ``0`` keeps everything.
   * - ``DATABASE_MAX_MB``
     - ``1024`` (1 GB)
     - The size the database is kept below, in megabytes; ``0`` for no limit. When fetches added data and none runs, the size is checked; above the limit, the data used longest ago is deleted until it is 10 % below it, so the next fetches do not start it again, and the database is compacted once. The projects stay and read their data again when needed.
   * - ``DATABASE_MIN_AGE_HOURS``
     - ``24``
     - Data fetched or looked at in these hours is never deleted to save space. If only such data is left, the database stays bigger than ``DATABASE_MAX_MB``, the *Cache* page says so, and the size is checked again when the first data is old enough.
   * - ``CACHALOT_ENABLED``
     - ``true``
     - ``false`` turns the cache of the statistics off.
   * - ``DATABASE_URL``
     - ``sqlite:///data/db.sqlite3``
     - Any database address understood by `dj-database-url <https://github.com/jazzband/dj-database-url>`_, such as ``postgres://user:password@host/name``.
   * - ``DATA_DIR``
     - ``./data`` (``/app/data`` in Docker)
     - Directory of the SQLite file and the secret key.
   * - ``ALLOWED_HOSTS``
     - ``*``
     - Comma separated host names.
   * - ``CSRF_TRUSTED_ORIGINS``
     - none
     - Comma separated origins like ``https://community.example.org``. Needed behind a TLS proxy.
   * - ``FETCH_CONCURRENCY``
     - ``4``
     - How many fetch jobs run at the same time.
   * - ``GITHUB_MAX_CONCURRENT``
     - ``20``
     - How many requests to GitHub the server sends at the same time, for all tokens together.
   * - ``FETCH_WORKER``
     - ``internal`` (development), ``external-http-container`` (the image)
     - Where the fetch worker runs, see :ref:`worker-modes`: ``internal`` (a thread of the web process), ``external-http-container`` (a process of its own in the web container), ``external-separate-container`` (only the ``worker`` service of the compose file; the web container runs none), ``inline`` (in the request, for tests). Another value stops the start with an error.
   * - ``VISITOR_SUBMITS_PER_HOUR``, ``VISITOR_FETCHES_PER_HOUR``
     - ``10``, ``5``
     - How many repositories a visitor without an account may add, and how many fetches start, per address and hour. Visitors share the tokens people donated, so one visitor cannot use them all up. ``0`` for no limit. People with an account have no such limit. ``django-ratelimit`` counts them in the cache (``CACHE_URL``), in windows of an hour; behind proxies, set ``TRUSTED_PROXIES`` so that the address of the visitor is counted, not that of the proxy.
   * - ``USER_MAX_ITEMS``
     - ``100000``
     - How many pull requests and issues the repositories of the projects of an account may hold; a fetch that would add more is refused. Administrators have no limit. ``0`` for no limit.
   * - ``TRUSTED_PROXIES``
     - ``0`` (development), ``1`` (the image)
     - How many proxies in front of the site add the address they were reached from to ``X-Forwarded-For``. The address of a visitor is the one the outermost of them added. The image has nginx in front: ``1``. Behind one more proxy with TLS, set ``2``. A number too high lets visitors choose their address.
   * - ``ACCOUNT_EMAIL_VERIFICATION``
     - ``optional``
     - ``none``, ``optional`` or ``mandatory``: whether people must confirm their email address.
   * - ``EMAIL_HOST``, ``EMAIL_PORT``, ``EMAIL_HOST_USER``, ``EMAIL_HOST_PASSWORD``, ``DEFAULT_FROM_EMAIL``
     - none, ``587``, none, none, ``webmaster@localhost``
     - The mail server for confirmation and password mails. Without ``EMAIL_HOST`` mails are written to the log.
   * - ``EMAIL_USE_TLS``, ``EMAIL_USE_SSL``
     - from ``EMAIL_PORT``
     - How the connection to the mail server is encrypted. ``EMAIL_USE_TLS`` starts in plain text and switches with STARTTLS, as port 587 does; ``EMAIL_USE_SSL`` speaks TLS from the start, as port 465 does. Without them, port 465 uses ``EMAIL_USE_SSL`` and every other port ``EMAIL_USE_TLS``. Both ``true`` stops the start (``EmailEncryptionConflict`` in :doc:`errors`). ``EMAIL_USE_TLS=false`` without ``EMAIL_USE_SSL`` sends without encryption, for a mail server on the same machine. The wrong one for the port fails with ``SMTPServerDisconnected: Connection unexpectedly closed``.
   * - ``PRODUCTION``
     - ``true``
     - A site others can reach. The container does not start while a superuser has a default password (``admin``, ``password``, or their own name). Set ``PRODUCTION=false`` for local test sites only. This is not ``DEBUG``.
   * - ``DEFAULT_SUPERUSER``
     - none
     - ``email:password``, such as ``admin@example.com:a-long-password``: each start of the container creates this superuser, or gives it this password and the rights of a superuser again. It signs in with the email address, which is also its name. Another form stops the start with the error *Invalid superuser* (see :doc:`errors`). With ``PRODUCTION`` on, a default password stops the start.
   * - ``DEBUG``
     - off
     - ``1`` turns on debug mode and the Django Debug Toolbar (development only). Never in production.
   * - ``GITHUB_API``
     - ``https://api.github.com``
     - The API address, for GitHub Enterprise.
   * - ``PRIVATE_REPOSITORIES``
     - ``false``
     - Private repositories are refused for now; ``true`` allows them.
   * - ``SOURCE_URL``, ``DOCS_URL``
     - ``https://github.com/PyCalendar/community-insights``, ``https://community-insights.readthedocs.io/en/latest/``
     - Where the code and the documentation of the running version are, for the links of the pages and the license; change them for a fork.
   * - ``PORT``
     - ``5000``
     - Port of gunicorn in the container.
   * - ``WORKERS``
     - ``1``
     - gunicorn worker processes. Each one needs about 300 MB, because it holds the libraries of the statistics; the fetch worker needs about 80 MB more. One worker with ``THREADS`` serves a small site. Measure a change with ``make benchmark`` (see :ref:`run-the-tests`).
   * - ``THREADS``
     - ``4``
     - gunicorn threads per worker.

The Docker image can use other databases only if the driver is installed in it; SQLite works out of the box.
