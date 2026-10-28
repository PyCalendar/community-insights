=========
Downloads
=========

**Data and sources** on every statistics page offers the tables behind its numbers, at ``/s/<scope>/data/<table>.<format>`` with the time range of the page. :doc:`../how-to/verify` shows how to compute the statistics from them.

Formats
=======

.. list-table::
   :header-rows: 1

   * - Format
     - Tables
     - What it holds
   * - ``csv``
     - all
     - one table with a header; a missing value is an empty cell
   * - ``json``
     - ``responses``
     - the facts of the download and the rows under ``rows``
   * - ``ods``
     - all
     - a spreadsheet made in the background: the table, the tables it was made from, and the sheet ``about``
   * - ``parquet``
     - all
     - one table with types: numbers, text, and times in UTC; the facts of the download as JSON under the key ``community-insights`` of the metadata of its schema

The facts of the download are: ``table``, ``repositories``, ``since``, ``until``, ``classes`` (each class with its column), ``exported_at`` and ``version``.

Tables
======

``responses``
    One row per pull request or issue created in the time range: ``repository``, ``kind`` (``pr`` or ``issue``), ``number``, ``author``, ``created_at``, ``state``, ``merged``, ``closed_at``, ``responded`` (``1`` if anybody else responded), ``seconds_any`` (the seconds until the first response of anybody), ``observed_seconds`` (how long it was watched: until it was closed or until the download), and ``seconds_<class>`` for each class of people, such as ``seconds_bot``, empty without a response of the class.

``items``
    One row per pull request or issue created in the time range: ``repository``, ``kind``, ``number``, ``title``, ``author``, ``author_association``, ``author_is_bot``, ``state``, ``merged``, ``merged_by``, ``created_at``, ``updated_at``, ``closed_at``.

``events``
    One row per opening, comment and review in the time range, oldest first: ``repository``, ``item_kind``, ``number``, ``kind``, ``actor``, ``association``, ``is_bot``, ``at``.

``commits``
    One row per commit of the default branch in the time range, oldest first: ``repository``, ``sha``, ``author``, ``author_name``, ``at``.

``contributors``
    One row per person, by handle: ``login``, ``class``, ``name``, ``location``, ``prs_opened``, ``prs_merged``, ``prs_closed_unmerged``, ``prs_open``, ``issues_opened``, ``issues_closed``, ``issues_open``, ``comments``, ``reviews``, ``commits``, ``median_response_seconds``, ``first_activity``, ``last_activity``, ``active_months``.

The times are ISO 8601 in UTC, such as ``2026-01-05T10:00:00Z``; Parquet has them as times. ``merged``, ``responded``, ``author_is_bot`` and ``is_bot`` are ``1`` or ``0``.

The query of the **Contributors** page is downloaded at ``/s/<scope>/contributors.csv`` and ``.ods``, with the columns of the query.
