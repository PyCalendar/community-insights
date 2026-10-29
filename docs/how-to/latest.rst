=========================
Use the latest version
=========================

Images are published to the GitHub container registry, ``ghcr.io/pycalendar/community-insights``:

``stable``
    the newest release, built when a version is tagged. Use this in production.

``latest``
    the newest commit of the ``main`` branch, for trying out what is not released yet.

``1.2.3``, ``1.2``
    a release, to stay on a version.

Images are only published when all tests passed. Each is built for ``linux/amd64`` and ``linux/arm64`` (for example a Raspberry Pi with a 64-bit system).

Update an installation with Compose:

.. code-block:: bash

    docker compose pull
    docker compose up -d

The database is migrated when the container starts (``manage.py prepare``). Until the site answers, Docker shows the container as *starting*, not *unhealthy*: failed health checks of the first five minutes do not count, so that tools which deploy and wait for a healthy container do not give up. Read the :doc:`../changelog` first, and back up ``data/``.

To run the newest code without Docker, see :doc:`develop`.
