========================
Query the contributors
========================

The **Contributors** page of a project lists everybody who opened, commented or reviewed something, in the time range chosen at the top. A query chooses who is shown, how they are sorted and grouped, and what the chart shows.

Who
===

A query compares variables with numbers or text and combines the comparisons with ``and``, ``or``, ``not`` and parentheses:

.. code-block:: text

    prs_merged >= 2 and days_last < 90 and not bot
    "berlin" in location or class == "maintainers"
    1 <= issues_opened < 10

Text is compared in any case with ``==``, ``!=``, ``in`` and ``not in``. **Variables** on the page lists all of them, such as ``prs_merged``, ``reviews``, ``response_hours`` (the median hours until their first response on the items of others), ``days_last``, ``location``, ``country`` (such as ``"DE"``) and ``horizon_europe``. A wrong name is answered with the names that are close.

Sort, group, columns, chart
===========================

* **Sort by** a variable; ``-reviews`` puts the biggest first.
* **Group by** the class of people, the location, the country, whether they are in Horizon Europe, or whether they are bots: a table sums the numbers of each group, and the chart shows the groups.
* **Columns** are variable names separated by spaces.
* **Chart of** a number shows the first 25 people or groups.

**Download as CSV** gives the table of the query. **Save** keeps the query under a name, to run it again later.

Time range
==========

Every statistics page has **From** and **To**: pull requests and issues created, and activity, in that time. The links, charts and downloads keep it.
