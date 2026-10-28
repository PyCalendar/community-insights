======================================
Tutorial: Set up your own installation
======================================

In this tutorial you run Contributor Community Insights with Docker Compose, sign up, add a project and see its statistics.

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
#. The dashboard asks for GitHub access. Choose **GitHub access** and follow :doc:`how-to/tokens` to create a token with an expiration date. Paste it and press **Add the token**.

3. Your first statistics
========================

#. On the dashboard choose the tab **Add repositories** and press **Refresh from GitHub**: your repositories, those of your organisations and those you contributed to are listed.
#. Type a part of a name to filter them, or type any ``owner/name`` or an organisation, and choose it.
#. Open the project from its card. The bar at the top says that 0% of the data is there.
#. Press **Read from GitHub**. The site estimates the API points and the time; press **Read from GitHub** again. The bar fills while the data comes in, and **Downloads** shows the fetch.
#. When the bar reaches 100%, the page shows the response times. Look at **Contributors**, open a person, and build a badge for your README at the bottom of the overview.

You have your own installation, with a project and its statistics.

Next steps
==========

- :doc:`how-to/configure`: sign in with GitHub, send mails, add an administrator and tokens for everybody, a separate worker, PostgreSQL and a public address.
- :doc:`how-to/use`: what the pages of the site do.
- :doc:`explanation/design`: how the site keeps the data and the ways to give it access to GitHub.
