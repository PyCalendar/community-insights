=====================
Use the application
=====================

Without an account
==================

The start page, **Explore**, lists the public repositories the site knows, with their numbers. Open one for its statistics, contributors, pull requests and issues and downloads; all of them work without signing in, with the default classes of people.

To add a public repository or organisation, type ``owner/name`` or ``owner`` and press **Add**. The site checks with the tokens people donated to it that it exists and is public. Then **Read from GitHub** shows how many points it needs and whether the donated tokens have them this hour; it reads with them, after the fetches of people with an account.

The address of public statistics names the repositories: ``/s/plone~volto/`` for one, ``/s/plone~volto+django~django/`` for several, ``/s/plone/`` for all known public repositories of an organisation. Their badges are at ``/badge/s/plone~volto.svg``.

With an account you can also keep projects, add your own tokens, save queries and change the classes of people.

Add projects
============

Open the **Dashboard**. Enter ``owner/name`` for one repository or only ``owner`` for a whole organisation or user. Your own repositories are listed on the right, most stars first, with a button to add each.

Press **Read from GitHub** on the overview. The first read of a large project takes minutes, later reads only fetch what changed.

Look at several projects
========================

Use **All together** on the dashboard, or the address ``/s/1-2-3/`` with the numbers of the projects.

Classes of people
=================

Response times are split by class of people. Open **Classes** to add your own, for example *maintainers* by a list of handles. See :doc:`../reference/classes`.

Badges
======

The overview has a badge builder. Choose pull requests or issues, the percentile, optionally a class and the text of the left side, and copy the code for Markdown, reStructuredText, HTML or the link. See :doc:`../reference/badges`.

Share
=====

**Share** at the top of a statistics page copies its address, with the time range and the query. **Share this chart** under a chart gives the code to show it elsewhere, linked to its page.

The response times on the overview are shown for one statistic at a time: **Statistic** chooses *measured*, *normal*, *exponential* or *Kaplan-Meier*. The one with the lowest standard error is chosen at first. Its *n* counts the items with a response of the class; for *Kaplan-Meier* it counts all items, because those without a response count as waiting.

Colours
=======

The button with the half circle in the menu chooses the colours of the page: *Auto* follows the system, *Light* and *Dark* stay. The charts change with the page.

Download files and read messages
================================

CSV and JSON files are downloaded at once. An ODS file has more sheets and can take a while: the link opens a page with a progress bar, and **Download** appears when the file is ready. You can leave the page; the file waits there for a week. With an account, a message tells you when it is ready: **Messages** in the menu shows the number of unread ones, and opening a message leads to the file. **Mark all as read** clears them. Visitors find their file on the page of the download, in the same browser.

Sort and name the columns
=========================

On the **Contributors** page, a click on the name of a column sorts the table by it, the biggest numbers or the text from A first; a second click sorts the other way. The **?** next to it explains the variable in the documentation. **Column names in words** shows what the columns mean instead of the names of the variables; the browser keeps the choice.

Clean the cache
===============

The **Cache** page lists the repositories from the one used longest ago. Delete the ones you do not need.
