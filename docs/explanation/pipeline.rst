=====================
Getting data
=====================

The site works in two steps:

#. **Get data**: read pull requests, issues, comments and reviews from GitHub into the database.
#. **Statistics**: every page computes its numbers from the data in the database. It never asks GitHub, so it is fast and works while GitHub is busy.

.. mermaid::

    flowchart LR
        page[Statistics page] -->|Read from GitHub| estimate[Estimate points and time]
        estimate -->|confirm, limit, priority| queue[(Queue)]
        queue --> worker[Worker]
        tokens[Tokens in order] --> worker
        worker -->|items as they are read| db[(Database)]
        db --> page

Every statistics page shows how complete its data is: the items downloaded of those on GitHub, how long until all are read, and the fetches that run. **Data and sources** lists the repositories, lets you choose which are shown and add more.

Estimate
========

Before reading, the site asks GitHub how many pull requests and issues there are (one API point for up to 50 repositories) and estimates the points: one per 50 items, some for items with many comments, and some for the people. The time is measured from earlier fetches. More than 5000 points, one hour of one token, need a limit.

The queue
=========

Each repository is a job. The worker runs the job with the highest priority first; this order also decides which job gets the tokens. On **Downloads** jobs can be moved up and down and cancelled. A cancelled job stops after its current request; everything read until then is kept. When all tokens are used up, the job waits until GitHub renews them.

.. _worker-modes:

Where the worker runs
---------------------

``FETCH_WORKER`` says where the jobs of the queue are run. There is always exactly one place:

.. list-table::
   :header-rows: 1

   * - Mode
     - Where
     - Used by
   * - ``internal``
     - a thread of the web process, started when a fetch is queued; it waits for jobs that wait for a rate limit and ends when the queue is empty
     - development: ``make run`` (the default of the settings)
   * - ``external-http-container``
     - a process of its own in the web container (``manage.py fetch_worker``), started again if it stops
     - the Docker image (its default) and ``docker compose`` as it comes
   * - ``external-separate-container``
     - only the ``worker`` service of ``docker-compose.yml``; the web container starts no worker
     - larger installations, see the :doc:`../tutorial`
   * - ``inline``
     - in the request that queued the fetch
     - the tests

In the external modes the worker also waits for rate limits to be renewed and cleans up the database. ``make worker`` runs the worker alone, as in its own container.

Requests
========

All requests to GitHub are asynchronous (`httpx <https://www.python-httpx.org/>`_), at an even pace below the limit of GitHub per minute (`aiolimiter <https://aiolimiter.readthedocs.io/en/stable/>`_). Several jobs run at the same time (``FETCH_CONCURRENCY``), and within a job the pull requests and the issues are read at the same time, and so are the comments of the items of a page and the batches of people.

GitHub limits more than the points per hour. The site stays below its secondary limits: at most 10 requests of a token at the same time, an even pace below 2000 points per minute, and at most ``GITHUB_MAX_CONCURRENT`` requests of the whole server, which all tokens share the address of. When GitHub still asks to slow down, the site waits as long as GitHub asks and tries again; longer waits move to the next token.

Few requests
============

* GraphQL reads 50 items with their first comments and reviews in one request: 1251 pull requests and issues of a real repository took 31 requests.
* Later fetches read only what changed since the last one: reading the same repository again took 2 requests.
* A fetch that stopped, cancelled or out of points, continues after the last page it read.
* The totals for the estimate are kept for 10 minutes, and asked for 50 repositories in one request.
* People are read again after 30 days, 30 in one request.
