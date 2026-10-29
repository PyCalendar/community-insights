======
Design
======

.. mermaid::

    flowchart LR
        user([User]) -->|sign in| gh[(GitHub)]
        user --> web[Django app]
        web -->|token of the user| gh
        web --> db[(Database: cache)]
        readme([README badge]) --> web

The cache
=========

Everything read from GitHub is stored in the database: repositories, pull requests, issues, and every comment or review as an *event* with its time, actor and status. The raw events are kept, not the response times, so changing the classes of people changes the results without reading GitHub again.

Every repository and person has ``fetched_at`` and ``last_used_at``. Pages that show a repository update the second one, at most once an hour. The cache page lists repositories from the oldest use, and ``manage.py clear_cache --days N`` deletes what was not used for N days; it is read again when needed. Syncs are incremental: items are read from the newest change back to the newest one stored.

.. _data-stamp:

Images and results kept until the data changes
==============================================

The statistics are computed from the stored events, and the same page shows the same numbers until the data changes. Computing them again for each visitor costs time and memory, so the site keeps them, together with a stamp of the data.

The library ``django-cachalot`` notes for each table when it was last written, in the cache that all processes share, and forgets its answers about that table. The stamp (``community_insights/data_stamp.py``) is a hash of these notes, the current hour and the version of the site:

- It stays the same while nobody writes: reading a page does not change it. This is why ``last_used_at`` is written at most once an hour; otherwise every page would change the stamp.
- A fetch, a new class of people or a changed project writes a table, so it changes the stamp.
- The hour is in it, because a pull request that waits for a response waits longer each hour without any change of the data.
- A note the cache lost is made again with the current time, so a stamp never goes back to older data.

The charts, their data for Chart.js and the badges are kept under the stamp, the address with its parameters, the user, the language and the time zone. Their answer has an ``ETag``: a browser that has the image asks with ``If-None-Match`` and gets ``304 Not Modified`` without the image. The contributors, which several pages and charts read, are kept the same way. Without cachalot (``CACHALOT_ENABLED=false``) nothing notes the changes, so nothing is kept.

.. _access-ways:

Ways to give access to GitHub
=============================

The site reads GitHub with the accounts and tokens of the people who use it. There are three ways to give it access, and they can be combined. The site reads with a linked GitHub account first, then with the tokens in their order, then with the points others share.

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

Tokens and privacy
==================

The token of the signed-in user reads GitHub. A project only contains repositories this token could see when it was added. Badges contain no token and read the database.

Response times
==============

A response is a comment or review by somebody other than the author. For each class the first response counts. The overview fits three models to the measured times: *measured* (average, median), *normal* and *exponential*, as in the earlier command line tool, and adds *Kaplan-Meier* for the items without a response. :doc:`response-times` explains how to read them.

The pages in the browser
========================

The pages work without JavaScript; scripts only add to them. Each script is in ``static/js/`` and reads what it needs from ``data-`` attributes, so the templates hold no code.

The charts are drawn twice. matplotlib draws them as SVG (``community_insights/charts.py``): an image to share, to embed elsewhere and to show without JavaScript. ``community_insights/chart_data.py`` gives the same charts as data, which Chart.js draws in the browser in place of the SVG, so that pointing at a bar shows its numbers. The SVG stays for the Kaplan-Meier curves, whose confidence bands Chart.js would draw less clearly.

Parts of a page that change while it is open, such as the progress of a fetch, are rendered by Django, like the rest of the page. htmx asks for them again and puts them into the page, so the text and its translation exist only once, in the template. When the fetch ends, the page is loaded again, with the statistics of the new data.

Libraries of the browser, such as Bootstrap, Chart.js, Sortable.js and htmx, are served from the site itself (``static/vendor/``), never from other servers: visitors are not tracked by them, and the site works without the internet.
