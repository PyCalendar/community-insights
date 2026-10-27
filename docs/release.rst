=======
Release
=======

Releases come from ``main``. Build the :ref:`change log <change-log>` from the news fragments, commit, and push a tag; after all tests passed, the workflow publishes the Docker image as ``stable``, ``1.2.3`` and ``1.2``.

.. code-block:: bash

    uv run --extra docs towncrier build --yes --version 1.2.0
    git commit -am "release 1.2.0"
    git tag v1.2.0
    git push origin main v1.2.0
