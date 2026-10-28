=============================
Configure your installation
=============================

These steps change an installation made with the :doc:`../tutorial`. Each one is independent: choose those you need. All settings are in ``.env``, see :doc:`../reference/configuration`; ``docker compose up -d`` applies them.

Let people sign in with GitHub
==============================

With a GitHub OAuth app people can sign in with GitHub, and their account is used as their first token.

#. Create the app as in :doc:`github-oauth`; the callback URL is ``http://localhost:5000/accounts/github/login/callback/`` or the one of your public address.
#. Put its values into ``.env``:

   .. code-block:: shell

       GITHUB_CLIENT_ID=Iv1.0123456789abcdef
       GITHUB_SECRET=0123456789abcdef0123456789abcdef01234567

#. Restart: ``docker compose up -d``. The start page now has **Sign in with GitHub**, and people who signed up with email can link GitHub on **GitHub access**.

The ways to give access can be combined, see :ref:`access-ways`.

Send mails
==========

For confirmation and password mails, add your mail server to ``.env``:

.. code-block:: shell

    EMAIL_HOST=smtp.example.org
    EMAIL_PORT=587
    EMAIL_HOST_USER=community@example.org
    EMAIL_HOST_PASSWORD=secret
    DEFAULT_FROM_EMAIL=community@example.org
    ACCOUNT_EMAIL_VERIFICATION=mandatory

Add an administrator
====================

The administration at ``/admin/`` shows all data; staff see **Admin** in the menu.

#. Put the email address and a long password of the superuser into ``.env``:

   .. code-block:: shell

       DEFAULT_SUPERUSER=admin@example.com:a-long-password-only-you-know

#. ``docker compose up -d``. Each start creates this superuser, or sets this password again.
#. Sign in with the email address, on the normal sign in page or at ``/admin/``.

To change the password, change it in ``.env`` and start again. A superuser without ``DEFAULT_SUPERUSER`` is created with:

.. code-block:: bash

    docker compose exec community-insights python manage.py createsuperuser

A site others can reach keeps ``PRODUCTION`` on, the default: then the container does not start while a superuser has a default password, such as ``admin`` or their own name, and says so in the log. Only a test site on your own computer may set ``PRODUCTION=false`` and use ``DEFAULT_SUPERUSER=admin@example.com:admin``.

Give everybody tokens of the site
=================================

People without a token of their own share 60 requests per hour. A superuser can add tokens that everybody on the site uses after their own:

.. code-block:: bash

    docker compose exec community-insights python manage.py add_shared_token admin@example.com github_pat_...

``--max-percent 50`` lets the site use only half of the points of the token per hour.

Run the worker in its own container
===================================

The fetch worker runs in the web container. To give it a container of its own:

#. Set in ``.env``:

   .. code-block:: shell

       FETCH_WORKER=external-separate-container

   Then the web container starts no worker.
#. Remove the comments of the ``worker`` service in ``docker-compose.yml``.
#. ``docker compose up -d``.

See :ref:`worker-modes` for all modes.

Use PostgreSQL
==============

SQLite in ``./data`` is fine for a few people. For more, use PostgreSQL: ``docker-compose.yml`` has a ``db`` service in comments. Remove the comments of it and of ``depends_on``, choose a password, and set in ``.env``:

.. code-block:: shell

    DATABASE_URL=postgres://community:community@db/community

The image has the driver. ``docker compose up -d`` creates the tables.


.. _configure-public-address:

Serve it at a public address
============================

Put a reverse proxy with TLS in front, such as Caddy or nginx, and set in ``.env``:

.. code-block:: shell

    ALLOWED_HOSTS=community.example.org
    CSRF_TRUSTED_ORIGINS=https://community.example.org

The proxy must send ``X-Forwarded-Proto`` and ``X-Forwarded-For``. The image counts its own nginx as one proxy (``TRUSTED_PROXIES=1``); with your proxy in front, set ``TRUSTED_PROXIES=2``, so that the limits of visitors count their address. Change the callback URL of the OAuth app to the new address.

Keep it up to date
==================

See :doc:`latest`. Back up ``./data`` first.
