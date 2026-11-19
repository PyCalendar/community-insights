=============
Read trends
=============

The page **Trends** of a project shows whether more or less happens: issues on one side, pull requests on the other. Each number of the time range stands next to the same number of the time just before it, and charts show it per day, week or month. This page explains what is counted.

The time range and the time before
==================================

Choose the time range at the top of the page: **Last 7 days**, **Last 30 days** or **Last 90 days**, or **From** and **To** for any dates. Every number is compared with the time of the same length that ends where the time range starts: the last 30 days with the 30 days before them, 1 to 14 March with 15 to 28 February. The page names the days of the time before.

All time has nothing before it, so the page shows the numbers without a change. The same holds for a time range with only **To**.

The page shows the change as a share of the time before, such as *+25 %* when 12 became 15. When the time before had none, the change is the number itself, such as *+3*.

What is counted
===============

opened
    The issues or pull requests opened in the time range, also those of bots, as on **Overview**.
closed
    The issues or pull requests closed in the time range, whenever they were opened. For pull requests, the merged ones are a part of them: *3/5 merged* means 3 of the 5 closed pull requests were merged.
contributions
    Openings, comments and reviews on issues or on pull requests by people, not bots. Below the number, how many people made them. Commits are not counted here: they belong to no issue or pull request (see **Contributors** for them).
new contributors
    The people, not bots, whose first contribution to issues, or to pull requests, is in the time range. They are listed by name under the charts. A person who opened an issue last year and their first pull request today is a new contributor to pull requests, but not to issues. Handles are compared without case, as on GitHub.

Bots are who GitHub marks as one, and handles that end with ``[bot]``.

New contributors are new to what the site has read
==================================================

The site only knows what it read from GitHub. A person is new when the site has no earlier contribution of theirs to these repositories. Read the whole history before trusting the new contributors: the bar at the top of the page shows how complete the data is. A project of several repositories counts the first contribution to any of them.

The charts
==========

Each side has two charts: opened and closed, and contributions and new contributors. A bar is a day for up to 31 days, a week from Monday for up to half a year, and a month for a longer time. Without a start of the time range, the charts start with the first issue, pull request or contribution. Days start at midnight in your time zone, shown at the bottom of the page.
