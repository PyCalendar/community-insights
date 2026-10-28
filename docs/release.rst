=======
Release
=======

Releases come from ``main``. Build the :ref:`change log <change-log>` from the news fragments, commit, and push a tag; after all tests passed, the workflow publishes the Docker image as ``stable``, ``1.2.3`` and ``1.2``.

.. code-block:: bash

    uv run --extra docs towncrier build --yes --version 1.2.0
    git commit -am "release 1.2.0"
    git tag v1.2.0
    git push origin main v1.2.0

The tag is the version: ``hatch-vcs`` reads it from git when the package is built, and ``docker/set-version.sh`` writes it into the image.
Between releases, the version counts the commits since the last tag, such as ``1.2.1.dev3+g3f7dc48``.
Without git, such as in an archive of the code, the version is ``0.0.0``.
Show the version of a checkout with:

.. code-block:: bash

    uvx --from hatchling==1.27.0 --with hatch-vcs==0.5.0 hatchling version
