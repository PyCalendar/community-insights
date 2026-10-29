========================
Query the contributors
========================

The **Contributors** page of a project lists everybody who opened, commented or reviewed something, in the time range chosen at the top. A query chooses who is shown, how they are sorted and grouped, and what the chart shows. :doc:`../reference/queries` lists every variable, operator and group.

Who
===

A query compares variables with numbers or text and combines the comparisons with ``and``, ``or``, ``not`` and parentheses:

.. code-block:: text

    prs_merged >= 2 and days_last < 90 and not user_bot
    "berlin" in user_location or user_class == "maintainers"
    1 <= issues_opened < 10

While you type a name, the field lists the variables that start with it: **Tab** takes the first one, the arrow keys choose another one and **Enter** takes it. Otherwise **Enter** runs the query. The result appears without loading the page again, and the page scrolls so that the query is at the top and the result below it; the address of the page changes with it, so you can share it. Choosing another **Group by** or **Chart of** runs the query, too.

Text is compared in any case with ``==``, ``!=``, ``in`` and ``not in``. **Variables** on the page lists all of them, such as ``prs_merged``, ``prs_reviewed``, ``commits_total``, ``hours_to_respond`` (the median hours until their first response on the items of others), ``days_last``, ``user_location``, ``user_country`` (such as ``"DE"``) and ``user_horizon_europe``. A wrong name is answered with the names that are close; an old name, with the one it has now.

Sort, group, columns, chart
===========================

* **Sort by** a variable; ``-prs_reviewed`` puts the biggest first.
* **Group by** the class of people, the location, the country, whether they are in Horizon Europe, or whether they are bots: a table sums the numbers of each group, and the chart shows the groups.
* **Columns** shows the columns of the table in their order. Drag a column to another place, or move it with the arrows next to its name; the cross removes it, and **+ add a column** adds one at the end. Without JavaScript, the columns are variable names separated by spaces.
* **Chart of** a number shows the first 25 people or groups.

**Download as CSV** gives the table of the query. **Save** keeps the query under a name, to run it again later.

.. _time-range:

Time range
==========

Every statistics page has **From** and **To**: pull requests and issues created, and activity, in that time. **Or the last days** sets a time range that moves with the days, such as ``30`` for the last 30 days with today. The time range is a part of the query: the links, charts and downloads keep it, the examples set their own, and a saved query keeps it.
