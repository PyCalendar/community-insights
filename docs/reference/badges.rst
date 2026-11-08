=======
Badges
=======

Every badge of the site comes in three formats: ``.svg``, ``.png`` for places that show no SVG, and ``.json``, its spec: ``schemaVersion``, ``label``, ``message`` and ``color`` in the format of `shields.io endpoint badges <https://shields.io/badges/endpoint-badge>`_, and what it counted besides. The pages that make badges switch between SVG and PNG, link the JSON, and show the code of the badge for **Markdown**, **reStructuredText**, **HTML** and its plain **URL**, each with a **Copy** button. The code links the badge to the page it comes from, so people who open it see where the number comes from.

A badge of a project has the secret badge token of the project in its address, so the address of a private project cannot be guessed; it counts with the classes of people of the owner. A badge of public repositories has the scope in its address, ``/badge/s/<scope>...``, and counts with the default classes.

.. _response-time-badges:

Response time
=============

``/badge/<token>.svg`` (``/badge/s/<scope>.svg`` for public repositories) shows the response time of a project. The JSON has what it counted: ``kind``, ``percentile``, ``class``, ``model``, ``seconds``, ``counted``. This badge reads the database only; it never calls GitHub and never uses a token. Update the data with **Update**.

.. list-table::
   :header-rows: 1

   * - Parameter
     - Default
     - Meaning
   * - ``kind``
     - ``pr``
     - ``pr`` or ``issue``
   * - ``percentile``
     - ``50``
     - 0 to 100: the time within which that share of first responses came
   * - ``class``
     - any
     - the name of a class of people; without it the first response of anyone counts
   * - ``model``
     - ``measured``
     - ``measured``, ``normal``, ``exponential`` or ``kaplan-meier``: how the percentile is computed, see :doc:`../explanation/response-times`. *Kaplan-Meier* also counts the items without a response and says *not reached* when that share never got one.
   * - ``label``
     - made from the others
     - the text of the left side, such as ``response time``; at most 60 characters

Example, the 95th percentile of the first response of collaborators to pull requests:

.. code-block:: markdown

    ![PR response](https://community.example.org/badge/TOKEN.svg?kind=pr&percentile=95&class=collaborator%20or%20higher)

Without data the badge says *no data*. An unknown class gives a 404. The builder on the page **Badges** of a project makes the code; it links the badge to the page **Response times**:

.. code-block:: rst

    .. image:: https://community.example.org/badge/TOKEN.svg?kind=pr&percentile=95
       :alt: pull request response time
       :target: https://community.example.org/s/plone~volto/

.. _reply-badges:

Badges of replies
=================

``/badge/<token>/replies/<login>.svg`` (``/badge/s/<scope>/replies/<login>.svg`` for public repositories) shows whether a person replied to the comments and reviews on their pull requests, as the page :doc:`replies` counts them. Its left side is the handle of the person; its right side says how many of the pull requests that count were not replied to, of all that count. It counts all their pull requests, without a time range.

These are all the badges a person can have, here for the handle ``kim``:

.. list-table::
   :header-rows: 1
   :widths: 30 10 60

   * - Badge
     - Colour
     - When
   * - .. image:: badges/replies-green.svg
          :alt: green badge, 0/3 PRs unanswered
     - .. _reply-badge-green:

       green
     - Every pull request that counts was replied to: *0/3 PRs unanswered*.
   * - .. image:: badges/replies-yellow.svg
          :alt: yellow badge, 1/1 PRs unanswered
     - .. _reply-badge-yellow:

       yellow
     - The person has only one pull request, it counts, and it was not replied to: *1/1 PRs unanswered*. Somebody new who may not know yet how a review works.
   * - .. image:: badges/replies-red.svg
          :alt: red badge, 2/3 PRs unanswered
     - .. _reply-badge-red:

       red
     - Some of their pull requests that count were not replied to, here 2 of 3.
   * - .. image:: badges/replies-grey.svg
          :alt: grey badge, no feedback yet
     - .. _reply-badge-grey:

       grey
     - *no feedback yet*: the person is not on the page of replies, as none of their pull requests counts. They opened none in the repositories, their pull requests were all merged or closed by themselves, they got no feedback or only approvals, the handle is not known, or the repositories were not read yet.

Which pull requests count is explained in :ref:`which-pull-requests-count`. The page of the badge (``/s/<scope>/replies/<login>/badge/``) shows the badge with its code and links here; the badge links to the replies of the person.

The JSON of the badge has the row of the table of replies: ``pull_requests``, ``merged``, ``counted``, ``with_feedback``, ``replied``, ``not_replied``, ``not_replied_open`` and ``not_replied_closed`` (the numbers by repository), ``closed_by_others``, ``status`` (``green``, ``yellow``, ``red``, or ``null`` for grey) and the ``page`` of the replies of the person.

Before it answers, a badge of replies reads what changed on GitHub if the repositories were read longer ago than ``AUTO_FETCH_AFTER_MINUTES``, waiting at most ``AUTO_FETCH_BADGE_TIMEOUT`` seconds, 4 by default (see :doc:`configuration`): GitHub shows the images of a README through its image proxy, which waits only a few seconds. A badge of a project reads with the tokens of its owner; a badge of public repositories with the tokens allowed for its badges and the points shared for everybody (see :ref:`public-uses`). Browsers and the image proxy keep each badge for an hour, so a README shows a new colour at most an hour later.

The examples above are made by the site itself: ``uv run python manage.py reply_badge_examples`` writes them again after a change of the badges; a test checks that they are up to date.

Share a chart
=============

Every chart has **Share this chart** under it. The page that opens shows the chart with its code in the same four formats, linked to the page the chart was on, with its time range and query. A chart reads the database only, like a badge. Everything shared opens without a sign in: a project is shared as its public repositories, such as ``/s/plone~volto+plone~plone.restapi/`` for ``/s/3/``, and the address keeps the time range, the query and your classes of people (``classes``), so others see the same numbers. A project without a public repository stays private: only you see it after you sign in, and the page says so. **Share** at the top of a statistics page copies the address of the page in the same way.
