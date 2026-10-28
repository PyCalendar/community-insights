==================
Run with Docker
==================

The image runs gunicorn, like `Open Web Calendar <https://open-web-calendar.quelltext.eu/>`_, behind nginx, which serves the static files. It listens on port 5000 (``PORT``) and creates or updates the database when it starts.

Docker Compose
==============

#. Save ``docker-compose.yml`` and ``.env`` next to each other. The files are in the repository; this is the compose file:

   .. literalinclude:: ../../docker-compose.yml
      :language: yaml

   and the environment file:

   .. literalinclude:: ../../.env.example
      :language: shell

#. Start it:

   .. code-block:: bash

       docker compose up -d

#. Open http://localhost:5000 and sign up. To sign in with GitHub, create the :doc:`OAuth app <github-oauth>` first.

The fetch worker runs in the same container as the web server (``FETCH_WORKER=external-http-container``, the default of the image). To run it in a container of its own, see :ref:`worker-modes` and the optional ``worker`` service of the compose file.

The ``./data`` directory holds the SQLite database and the generated secret key. Back it up, or set ``DATABASE_URL`` to use another database (see :doc:`../reference/configuration`).

Without Compose
===============

.. code-block:: bash

    docker run -d -p 5000:5000 -v "$PWD/data:/app/data" --env-file .env \
        ghcr.io/pycalendar/community-insights:stable

Log rotation
============

The site writes every request and every fetch to its log, so the logs grow. The compose file rotates them with Docker's own logging: at most five files of 10 MB for each service (``x-logging`` at its top). Change ``max-size`` and ``max-file`` there.

To rotate the logs of all containers of the server, also those started with ``docker run``, set the same in ``/etc/docker/daemon.json`` and restart Docker:

.. code-block:: json

    {
      "log-driver": "json-file",
      "log-opts": {"max-size": "10m", "max-file": "5"}
    }

The setting applies to containers created after the restart: ``docker compose up -d --force-recreate`` creates them again. ``docker compose logs`` still shows the logs.

Behind a reverse proxy
======================

See :ref:`configure-public-address`.

Build the image yourself
========================

.. code-block:: bash

    make docker-build     # same as: docker build -t community-insights .
    make docker-run

The Dockerfile:

.. literalinclude:: ../../Dockerfile
   :language: docker
