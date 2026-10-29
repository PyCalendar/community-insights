.. _variables:

===============
Query variables
===============

The variables of a query: the columns of the contributors table, what **Who** compares, what the table is sorted and grouped by and what the chart shows. Each is counted for one person in the time range of the page (**From** and **To**, or the last days): pull requests and issues created in it, and comments, reviews and commits made in it. :doc:`query-operators` lists how to compare and combine them; :doc:`../explanation/queries` explains how a query is built.

The column headers of the table link here. Each variable is a column, can be compared in **Who**, sorted by, and, for numbers, summed up in groups and shown in the chart. The names are grouped by what they are about, with a prefix: ``user_``, ``commits_``, ``prs_``, ``issues_``, ``comments_``, ``actions_`` and ``activity_``, or the unit first: ``hours_``, ``days_``, ``months_``. They are the names of the command line tool before this site.

.. list-table::
   :header-rows: 1
   :widths: 30 10 60

   * - Variable
     - Kind
     - Meaning
   * - :ref:`actions_merges <variable-actions_merges>`
     - number
     - Pull requests merged by them
   * - :ref:`activity_total <variable-activity_total>`
     - number
     - Pull requests, issues, comments, reviews and commits
   * - :ref:`comments_total <variable-comments_total>`
     - number
     - Comments on items of others
   * - :ref:`commits_total <variable-commits_total>`
     - number
     - Commits
   * - :ref:`days_first <variable-days_first>`
     - number
     - Days since the first activity
   * - :ref:`days_last <variable-days_last>`
     - number
     - Days since the last activity
   * - :ref:`days_to_merge <variable-days_to_merge>`
     - number
     - Median days until their pull requests were merged
   * - :ref:`hours_to_respond <variable-hours_to_respond>`
     - number
     - Median time until their first response on items of others
   * - :ref:`issues_closed <variable-issues_closed>`
     - number
     - Issues closed
   * - :ref:`issues_commented <variable-issues_commented>`
     - number
     - Issues of others commented on
   * - :ref:`issues_open <variable-issues_open>`
     - number
     - Issues still open
   * - :ref:`issues_opened <variable-issues_opened>`
     - number
     - Issues opened
   * - :ref:`months_active <variable-months_active>`
     - number
     - Months with any activity
   * - :ref:`prs_closed <variable-prs_closed>`
     - number
     - Pull requests closed, merged or not
   * - :ref:`prs_commented <variable-prs_commented>`
     - number
     - Pull requests of others commented on
   * - :ref:`prs_merged <variable-prs_merged>`
     - number
     - Pull requests merged
   * - :ref:`prs_open <variable-prs_open>`
     - number
     - Pull requests still open
   * - :ref:`prs_reviewed <variable-prs_reviewed>`
     - number
     - Pull requests of others reviewed
   * - :ref:`prs_total <variable-prs_total>`
     - number
     - Pull requests opened
   * - :ref:`prs_unmerged <variable-prs_unmerged>`
     - number
     - Pull requests closed without merging
   * - :ref:`user_association <variable-user_association>`
     - text
     - Most privileged status seen, such as member or contributor
   * - :ref:`user_bot <variable-user_bot>`
     - bool
     - True for bots
   * - :ref:`user_class <variable-user_class>`
     - text
     - Class of people
   * - :ref:`user_country <variable-user_country>`
     - text
     - Country of the location (ISO code, such as DE)
   * - :ref:`user_handle <variable-user_handle>`
     - text
     - GitHub handle
   * - :ref:`user_horizon_europe <variable-user_horizon_europe>`
     - bool
     - True for locations in Horizon Europe
   * - :ref:`user_location <variable-user_location>`
     - text
     - Location in the GitHub profile
   * - :ref:`user_name <variable-user_name>`
     - text
     - Name in the GitHub profile

.. _variable-actions_merges:

actions_merges
--------------

*number*: Pull requests merged by them.

How many pull requests the person merged in the time range, also those of others.

.. _variable-activity_total:

activity_total
--------------

*number*: Pull requests, issues, comments, reviews and commits.

Everything together: pull requests and issues opened, comments, reviews and commits. Sorting by ``-activity_total`` puts the busiest first.

.. _variable-comments_total:

comments_total
--------------

*number*: Comments on items of others.

All comments the person wrote on pull requests and issues of others in the time range. Comments on their own items do not count.

.. _variable-commits_total:

commits_total
-------------

*number*: Commits.

The commits of the person on the default branch in the time range, counted by their GitHub account.

.. _variable-days_first:

days_first
----------

*number*: Days since the first activity.

Days since the first activity of the person in the time range: small numbers are newcomers.

.. _variable-days_last:

days_last
---------

*number*: Days since the last activity.

Days since the last activity of the person: small numbers are active now, big ones left.

.. _variable-days_to_merge:

days_to_merge
-------------

*number*: Median days until their pull requests were merged.

The median of the days from opening to merging of the pull requests of the person that were merged in the time range. Infinite, shown as ``-``, without merged pull requests.

.. _variable-hours_to_respond:

hours_to_respond
----------------

*number*: Median time until their first response on items of others.

The median of the hours until the person's first response, a comment or review, on items of others: half of their first responses came faster. Infinite, shown as ``-``, for people who never responded to others. The table shows it as a time, such as ``2d 4h`` or ``3h 12min``; a query compares the hours, such as ``hours_to_respond <= 24``.

.. _variable-issues_closed:

issues_closed
-------------

*number*: Issues closed.

Of the issues the person opened, those that are closed, shown as a part of ``issues_opened``.

.. _variable-issues_commented:

issues_commented
----------------

*number*: Issues of others commented on.

How many issues of others the person commented on in the time range; several comments on one count once.

.. _variable-issues_open:

issues_open
-----------

*number*: Issues still open.

Of the issues the person opened, those that are still open, shown as a part of ``issues_opened``.

.. _variable-issues_opened:

issues_opened
-------------

*number*: Issues opened.

The issues the person opened in the time range.

.. _variable-months_active:

months_active
-------------

*number*: Months with any activity.

In how many months the person did anything: opened, commented, reviewed or committed.

.. _variable-prs_closed:

prs_closed
----------

*number*: Pull requests closed, merged or not.

Of the pull requests the person opened, those that are closed, merged or not: ``prs_merged`` and ``prs_unmerged`` together, shown as a part of ``prs_total``.

.. _variable-prs_commented:

prs_commented
-------------

*number*: Pull requests of others commented on.

How many pull requests of others the person commented on in the time range; several comments on one count once.

.. _variable-prs_merged:

prs_merged
----------

*number*: Pull requests merged.

Of the pull requests the person opened, those that were merged. The table shows it as a part of ``prs_total``, such as ``3/5``: three of five merged.

.. _variable-prs_open:

prs_open
--------

*number*: Pull requests still open.

Of the pull requests the person opened, those that are still open, shown as a part of ``prs_total``.

.. _variable-prs_reviewed:

prs_reviewed
------------

*number*: Pull requests of others reviewed.

How many pull requests of others the person reviewed in the time range; several reviews of one count once.

.. _variable-prs_total:

prs_total
---------

*number*: Pull requests opened.

The pull requests the person opened in the time range.

.. _variable-prs_unmerged:

prs_unmerged
------------

*number*: Pull requests closed without merging.

Of the pull requests the person opened, those that were closed without merging, shown as a part of ``prs_total``.

.. _variable-user_association:

user_association
----------------

*text*: Most privileged status seen, such as member or contributor.

The status of the person in the repositories, as GitHub tells it with their comments and reviews, in lowercase: the most privileged one seen, in this order: ``owner``, ``member``, ``collaborator``, ``contributor``, ``first_timer``, ``first_time_contributor``, ``mannequin``, ``none``. Empty if they only opened items.

.. _variable-user_bot:

user_bot
--------

*bool*: True for bots.

True for the people in the class *bot*, and for handles that end with ``[bot]``.

.. _variable-user_class:

user_class
----------

*text*: Class of people.

The class of people the person belongs to: the first class whose rules match, see :doc:`classes`.

.. _variable-user_country:

user_country
------------

*text*: Country of the location (ISO code, such as DE).

The country of the location as a two-letter code, such as ``DE``; empty if the location names none. :doc:`locations` explains how the country is found.

.. _variable-user_handle:

user_handle
-----------

*text*: GitHub handle.

The handle on GitHub, such as ``octocat``. The table links it to the page of the person.

.. _variable-user_horizon_europe:

user_horizon_europe
-------------------

*bool*: True for locations in Horizon Europe.

True for locations in a country of Horizon Europe, see :doc:`locations`.

.. _variable-user_location:

user_location
-------------

*text*: Location in the GitHub profile.

The location the person wrote in their GitHub profile, as they wrote it, such as ``Berlin, Germany`` or ``the internet``.

.. _variable-user_name:

user_name
---------

*text*: Name in the GitHub profile.

The name the person wrote in their GitHub profile; empty if there is none, or if the repositories were read without a token.

Kinds of variables
==================

number
    A whole number or a number with a decimal point. ``hours_to_respond``, ``days_to_merge``, ``days_first`` and ``days_last`` are infinite for people without a response or without activity; the table shows them as ``-``, and they come last when sorted by the smallest first.
text
    Compared in any case: ``user_location == "berlin"`` matches *Berlin*.
bool
    ``True`` or ``False``, used alone or with ``not``: ``not user_bot``. ``user_bot`` is true for the people in the class *bot* and for handles that end with ``[bot]``.
