=======
Queries
=======

A query chooses the people of the **Contributors** page of a statistics page, how they are sorted and grouped, which columns are shown and what the chart shows. This page lists its parameters; :doc:`query-variables` lists the variables, :doc:`query-operators` the operators of **Who**. :doc:`../how-to/queries` shows how to write one, :doc:`../explanation/queries` how a query is built.

The numbers count what happened in the time range of the page (**From** and **To**): pull requests and issues created in it, and comments, reviews and commits made in it.

Examples
========

The page offers these examples under **Who**. An example with a time range sets it; the others keep the time range of the page.

.. list-table::
   :header-rows: 1
   :widths: 30 40 15 15

   * - Who
     - Query
     - Sort by
     - Time range
   * - most commits in the last month
     - ``commits_total > 0``
     - ``-commits_total``
     - last 30 days
   * - external contributors who opened a pull request in the last month
     - ``user_class == "external" and prs_total > 0``
     - ``-prs_total``
     - last 30 days
   * - new, but contributed continuously in the last two months
     - ``days_last < 60 and not user_bot and prs_total > 3 and commits_total < 300 and prs_reviewed < 1``
     - ``-prs_total``
     - last 60 days
   * - who opened a pull request, the most merged first
     - ``prs_total > 0``
     - ``-prs_merged``
     - the one of the page
   * - who reviews the pull requests of others
     - ``prs_reviewed > 0 and not user_bot``
     - ``-prs_reviewed``
     - the one of the page
   * - who answers within a day
     - ``hours_to_respond <= 24 and not user_bot``
     - ``hours_to_respond``
     - the one of the page
   * - people in a country of Horizon Europe
     - ``user_horizon_europe and not user_bot``
     - ``-activity_total``
     - the one of the page
   * - opened issues, but no pull request
     - ``issues_opened > 0 and prs_total == 0``
     - ``-issues_opened``
     - the one of the page

Sort by
=======

A variable sorts the people by it, the smallest first; ``-`` in front of it puts the biggest first. Empty means ``-activity_total``.

.. _group-by:

Group by
========

``user_class``, ``user_association``, ``user_location``, ``user_country``, ``user_horizon_europe``, ``user_bot``. A table then shows one row per value with the number of people and the sums of all numbers of the variables; infinite values are left out of the sums. People without a value are in the group ``(none)``. The groups with the most people come first.

Columns
=======

The variables to show as columns, in their order; empty means the default columns:

``user_handle``, ``user_class``, ``commits_total``, ``prs_merged``, ``issues_opened``, ``comments_total``, ``prs_reviewed``, ``hours_to_respond``, ``user_location``, ``days_last``.

On the page, the columns are moved by drag and drop or the arrows, removed with the cross and added from the list. Without JavaScript, they are the names separated by spaces.

Chart of
========

A variable of the kind number. The chart shows the first 25 people or groups, by this number.

In the address
==============

The query is kept in the address of the page, so a link or **Share** shows the same result: ``where``, ``sort``, ``columns``, ``group``, ``chart`` and the time range ``since``, ``until`` or ``last``, such as ``/s/plone~volto/contributors/?where=not+user_bot&sort=-prs_reviewed&group=user_country&last=30``. A saved query keeps its time range, too. The downloads take the same parameters.

Errors
======

A query that cannot be used is shown with what is wrong, a link to its description and a link to :doc:`../how-to/queries`:

.. vale off

- :class:`~community_insights.errors.input.QueryNotReadable`: the text is no expression.
- :class:`~community_insights.errors.input.UnknownVariable`: a name is no variable; the message names those that are close.
- :class:`~community_insights.errors.input.NotAComparison`: a part compares nothing.
- :class:`~community_insights.errors.input.NotAValue`: a side of a comparison is no variable, number or text.
- :class:`~community_insights.errors.input.UnsupportedComparison`: an operator that cannot be used, such as ``is``.
- :class:`~community_insights.errors.input.TextComparedWithNumber`: text is compared with a number.
- :class:`~community_insights.errors.input.WrongOperatorForText`: text is compared with ``<`` or ``>``.
- :class:`~community_insights.errors.input.UnknownGroup`: the group is none of those above.

.. vale on
