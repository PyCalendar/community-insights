=====
URLs
=====

.. list-table::
   :header-rows: 1

   * - Address
     - Page
   * - ``/dashboard/``
     - projects, adding projects, your repositories
   * - ``/s/<scope>/``
     - overview: counts, response time charts and tables, badge builder
   * - ``/s/<scope>/contributors/``
     - contributors table; ``q``, ``class`` and ``sort`` filter it
   * - ``/s/<scope>/people/<login>/``
     - one person: contributions per month, hours of the day, weekday and hour heat map
   * - ``/s/<scope>/share/<chart>/``
     - the code to share a chart; ``from`` is the page it links to
   * - ``/documents/<id>/``
     - a file made in the background: its progress and its download (``download/``)
   * - ``/messages/``
     - the messages of the account, such as that a file is ready
   * - ``/s/<scope>/fetch/``
     - estimate and start reading from GitHub
   * - ``/s/<scope>/data/<table>.csv``
     - the data behind the statistics, see :doc:`../how-to/verify`
   * - ``/s/<scope>/progress.json``
     - how complete the data is
   * - ``/dashboard/downloads/``
     - running and queued fetches
   * - ``/dashboard/github/``
     - tokens and profile
   * - ``/dashboard/classes/``
     - classes of people
   * - ``/dashboard/cache/``
     - cached repositories from the oldest use
   * - ``/badge/<token>.svg``
     - :doc:`badges`

The ``<scope>`` is a project number, several joined by ``-`` (``1-3``) or ``all``: these need a sign in. Or public repositories for everybody: ``owner~name``, several joined by ``+``, or ``owner`` for all known public repositories of an owner. ``/explore/`` lists the public repositories; ``/badge/s/<scope>.svg`` is the badge of a public scope. Times are shown in the time zone of the browser, which sends it in the cookie ``tz``. Every statistics page takes the time range ``since``, ``until`` or ``last``, and ``classes``: the ids of the classes of people to use, see :ref:`shared-statistics`.
