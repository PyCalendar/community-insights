============================
Set up your own installation
============================

In this tutorial you run Contributor Community Insights with Docker Compose, sign up, and give it access to GitHub.

You need `Docker with Compose <https://docs.docker.com/compose/install/>`_ and about 10 minutes.

1. Start it
===========

#. Make a directory and get the two files:

   .. code-block:: bash

       mkdir community && cd community
       curl -LO https://raw.githubusercontent.com/PyCalendar/community-insights/main/docker-compose.yml
       curl -L -o .env https://raw.githubusercontent.com/PyCalendar/community-insights/main/.env.example

   ``docker-compose.yml``:

   .. literalinclude:: ../../docker-compose.yml
      :language: yaml

#. Choose the superuser who administrates the site, **before the first start**. Put an email address and a long password into ``.env``:

   .. code-block:: shell

       DEFAULT_SUPERUSER=admin@example.com:a-long-password-only-you-know

   Each start creates this superuser, or gives it this password again. It signs in with the email address. A default password such as ``admin`` stops the start: the site is for others to reach (``PRODUCTION`` is on).

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
#. The dashboard asks for GitHub access. Choose **GitHub access** and follow :doc:`../how-to/tokens` to create a token with an expiration date. Paste it and press **Add the token**.

You have your own installation, with an account that can read GitHub. Go on with :doc:`first-project`.

Next steps
==========

- :doc:`first-project`: add a project and read its statistics.
- :doc:`../how-to/configure`: sign in with GitHub, send mails, add an administrator and tokens for everybody, a separate worker, PostgreSQL and a public address.
- :doc:`../explanation/design`: how the site keeps the data and the ways to give it access to GitHub.
