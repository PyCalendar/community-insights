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

Every repository and person has ``fetched_at`` and ``last_used_at``. Pages that show a repository update the second one. The cache page lists repositories from the oldest use, and ``manage.py clear_cache --days N`` deletes what was not used for N days; it is read again when needed. Syncs are incremental: items are read from the newest change back to the newest one stored.

Tokens and privacy
==================

The token of the signed-in user reads GitHub. A project only contains repositories this token could see when it was added. Badges contain no token and read the database.

Response times
==============

A response is a comment or review by somebody other than the author. For each class the first response counts. The overview fits three models to the measured times: *measured* (average, median), *normal* and *exponential*, as in the earlier command line tool.
