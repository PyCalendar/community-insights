======================================
Tutorial: Set up your own installation
======================================

In this tutorial you run Contributor Community Insights with Docker Compose, sign in, add a project and see its statistics. Then you choose the optional steps you need: signing in with GitHub, mails, an administrator, a separate worker, PostgreSQL and a public address.

You need `Docker with Compose <https://docs.docker.com/compose/install/>`_ and about 15 minutes.

1. Start it
===========

#. Make a directory and get the two files:

   .. code-block:: bash

       mkdir community && cd community
       curl -LO https://raw.githubusercontent.com/PyCalendar/community-insights/main/docker-compose.yml
       curl -L -o .env https://raw.githubusercontent.com/PyCalendar/community-insights/main/.env.example

   ``docker-compose.yml``:

   .. literalinclude:: ../docker-compose.yml
      :language: yaml

#. Choose the superuser who administrates the site, **before the first start**. Put a name and a long password into ``.env``:

   .. code-block:: shell

       DEFAULT_SUPERUSER=admin:a-long-password-only-you-know

   The first start creates this superuser. A default password such as ``admin`` stops the start: the site is for others to reach (``PRODUCTION`` is on). After the first start, remove the line from ``.env``; the superuser and the password stay.

#. Start it:

   .. code-block:: bash

       docker compose up -d
       docker compose logs -f     # Ctrl+C to stop watching

   It creates the database in ``./data`` and listens on port 5000.

#. Open http://localhost:5000. You see the start page.

2. Sign up and add a token
==========================

Without any configuration people sign up with an email address and a password, and give the site access to GitHub with a token.

#. Choose **Sign up with email**, enter an address and a password. Without a mail server the confirmation mail is only written to the log (``docker compose logs``); with ``ACCOUNT_EMAIL_VERIFICATION=optional`` (the default) you can go on without confirming.
#. The dashboard asks for GitHub access. Choose **GitHub access** and follow :doc:`how-to/tokens` to create a token with an expiration date. Paste it and press **Add the token**.

3. Your first statistics
========================

#. On the dashboard choose the tab **Add repositories** and press **Refresh from GitHub**: your repositories, those of your organisations and those you contributed to are listed.
#. Type a part of a name to filter them, or type any ``owner/name`` or an organisation, and choose it.
#. Open the project from its card. The bar at the top says that 0% of the data is there.
#. Press **Read from GitHub**. The site estimates the API points and the time; press **Read from GitHub** again. The bar fills while the data comes in, and **Downloads** shows the fetch.
#. When the bar reaches 100%, the page shows the response times. Look at **Contributors**, open a person, and build a badge for your README at the bottom of the overview.

That is the whole setup. The next steps are optional.

Optional: Sign in with GitHub
=============================

With a GitHub OAuth app people can sign in with GitHub, and their account is used as their first token.

#. Create the app as in :doc:`how-to/github-oauth`; the callback URL is ``http://localhost:5000/accounts/github/login/callback/`` or the one of your public address.
#. Put its values into ``.env``:

   .. code-block:: shell

       GITHUB_CLIENT_ID=Iv1.0123456789abcdef
       GITHUB_SECRET=0123456789abcdef0123456789abcdef01234567

#. Restart: ``docker compose up -d``. The start page now has **Sign in with GitHub**, and people who signed up with email can link GitHub on **GitHub access**.

The three ways to give access can be combined; they are used in this order:

.. list-table::
   :header-rows: 1

   * - Way
     - Needs
     - Good for
   * - Email and password, then tokens
     - nothing
     - any installation; friends can give tokens
   * - Sign in with GitHub
     - an OAuth app
     - the easiest for people; the account is the first token
   * - Email first, link GitHub later
     - an OAuth app
     - people who want both

Optional: Send mails
====================

For confirmation and password mails, add your mail server to ``.env``:

.. code-block:: shell

    EMAIL_HOST=smtp.example.org
    EMAIL_PORT=587
    EMAIL_HOST_USER=community@example.org
    EMAIL_HOST_PASSWORD=secret
    DEFAULT_FROM_EMAIL=community@example.org
    ACCOUNT_EMAIL_VERIFICATION=mandatory

Optional: An administrator
==========================

The administration at ``/admin/`` shows all data. Create a superuser:

.. code-block:: bash

    docker compose exec community-insights python manage.py createsuperuser

Sign in at http://localhost:5000/admin/ with the name and password, or on the normal sign in page with the email address. Staff see **Admin** in the menu.

For a test site, ``DEFAULT_SUPERUSER=admin:admin`` and ``PRODUCTION=false`` in ``.env`` create the superuser ``admin`` with the password ``admin`` at start (email ``admin@example.org``).

A site others can reach keeps ``PRODUCTION`` on (the default). Then the container does not start while a superuser has a default password such as ``admin`` or their own name, and says so in the log. Change the password, signed in at ``/accounts/password/change/`` or with:

.. code-block:: bash

    docker compose exec community-insights python manage.py changepassword admin

The admin is signed in to like the rest of the site, which limits failed attempts.

Optional: Tokens for everybody
==============================

People without a token of their own share 60 requests per hour. A superuser can add tokens that everybody on the site uses after their own:

.. code-block:: bash

    docker compose exec community-insights python manage.py add_shared_token admin github_pat_...

``--max-percent 50`` lets the site use only half of the points of the token per hour.

Optional: A separate worker
===========================

The fetch worker runs in the web container. To give it a container of its own:

#. Set in ``.env``:

   .. code-block:: shell

       FETCH_WORKER=external-separate-container

   Then the web container starts no worker.
#. Remove the comments of the ``worker`` service in ``docker-compose.yml``.
#. ``docker compose up -d``.

See :ref:`worker-modes` for all modes.

Optional: PostgreSQL
====================

SQLite in ``./data`` is fine for a few people. For more, use PostgreSQL: ``docker-compose.yml`` has a ``db`` service in comments. Remove the comments of it and of ``depends_on``, choose a password, and set in ``.env``:

.. code-block:: shell

    DATABASE_URL=postgres://community:community@db/community

The image has the driver. ``docker compose up -d`` creates the tables.

Optional: A public address
==========================

Put a reverse proxy with TLS in front, such as Caddy or nginx, and set in ``.env``:

.. code-block:: shell

    ALLOWED_HOSTS=community.example.org
    CSRF_TRUSTED_ORIGINS=https://community.example.org

The proxy must send ``X-Forwarded-Proto``. Change the callback URL of the OAuth app to the new address.

Keep it up to date
==================

See :doc:`how-to/latest`. Back up ``./data`` first.
