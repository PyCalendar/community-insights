=====================
Use the application
=====================

Without an account
==================

The start page, **Explore**, lists the public repositories the site knows, with their numbers. Open one for its statistics, contributors, pull requests and issues and downloads; all of them work without signing in, with the default classes of people.

To add a public repository or organisation, type ``owner/name`` or ``owner`` and press **Add**. The site checks with the tokens people donated to it that it exists and is public. **Update** then reads it at once; the drop-down next to it shows how many points a fetch needs and whether the donated tokens have them.

The address of public statistics names the repositories: ``/s/plone~volto/`` for one, ``/s/plone~volto+django~django/`` for several, ``/s/plone/`` for all known public repositories of an organisation. Their badges are at ``/badge/s/plone~volto.svg``, and the badges of replies at ``/badge/s/plone~volto/replies/<login>.svg``.

With an account you can also keep projects, add your own tokens, save queries and change the classes of people.

Signed in, the button **Account** at the top opens a menu with your pages: **Dashboard**, **Explore**, **Messages** and **Downloads**; **Profile**, **GitHub access** and **Classes**; for administrators **Cache**, **Admin** and **Users** (see :doc:`users`); and **Sign out**.

Add projects
============

Open the **Dashboard** and the tab **Add repositories**. **Refresh from GitHub** lists your repositories, those of your organisations and those you contributed to; type a part of a name to filter them, or any ``owner/name`` or ``owner`` for a whole organisation or user, and choose it.

Press **Update** on the overview, or on the card of the project on the dashboard. It reads at once all the pages need: what changed, and what earlier reads missed. The first read of a large project takes minutes, later reads only fetch what changed. The drop-down next to **Update** opens the page that estimates the points and time and chooses what and how much to read.

Look at several projects
========================

Use **All together** on the dashboard, or the address ``/s/1-2-3/`` with the numbers of the projects.

.. _use-classes:

Change the classes of people
============================

Response times are split by class of people. Open **Classes** in the menu **Account**:

- To add a class, for example *maintainers* by a list of handles, fill in the form for a new class; :doc:`../reference/class-rules` lists the kinds of rules.
- To change the order, drag a class by its handle ⠿ to another place, or move it with the arrows. Somebody belongs to the first class with a rule that matches.
- To rename a class or change its colour, change the fields at the top of the class and press **Save**.
- A class of the site cannot be deleted: **Hide** keeps it sorting people, but the statistics do not show it.

See :doc:`../reference/classes` for the default classes.

Read the response times
=======================

The overview shows, for pull requests and for issues:

- the bars of the times until the first response of each class; point at a bar to see its numbers,
- the curve of the share still waiting for a response (Kaplan-Meier),
- the table of one statistic: **Statistic** chooses *measured*, *normal*, *exponential* or *Kaplan-Meier*, at first the one with the lowest standard error,
- the trend: whether the first responses get faster or slower per month.

:doc:`../explanation/response-times` explains how to read each of them.

Who replies to feedback
=======================

**Replies** shows whether the authors of pull requests replied to the comments and reviews they got, with a coloured label for each person; the label opens the replies of the person, with all their pull requests and their badge. :doc:`../tutorials/replies` goes through it step by step, and :doc:`../reference/replies` explains which pull requests count. The page and the badges read what changed on GitHub first, a few seconds at most.

Badges
======

The overview has a builder of the badge of the response time: choose pull requests or issues, the percentile, optionally a class, the statistic, the text of the left side and SVG or PNG, and copy the code for Markdown, reStructuredText, HTML or the plain URL. Each person on **Replies** has a badge of their replies, with its own page and code. Every badge is also JSON. :doc:`../reference/badges` lists the badges and their colours.

Share
=====

**Share** at the top of a statistics page copies its address, with the time range, the query and your classes of people. **Share this chart** under a chart gives the code to show it elsewhere, linked to its page. Both open without a sign in: your projects are shared as their public repositories.

Colours and language
====================

The button with the half circle in the menu chooses the colours of the page: *Auto* follows the system, *Light* and *Dark* stay. The charts change with the page.

The pages are in the language of the browser: English, German or Spanish. The choice at the bottom of every page changes it; see :doc:`translate`.

Download files and read messages
================================

CSV, Parquet and JSON files are downloaded at once; :doc:`../reference/downloads` lists their columns. An ODS file has more sheets and can take a while: the link opens a page with a progress bar, and **Download** appears when the file is ready. You can leave the page; the file waits there for a week. With an account, a message tells you when it is ready: **Messages** in the menu **Account** shows the number of unread ones (the button **Account** shows it, too), and opening a message leads to the file. **Mark all as read** clears them. Visitors find their file on the page of the download, in the same browser.

Sort and name the columns
=========================

On the **Contributors** page, a click on the name of a column sorts the table by it, the biggest numbers or the text from A first; a second click sorts the other way. The **?** next to it explains the variable in the documentation. **Column names in words** shows what the columns mean instead of the names of the variables; the browser keeps the choice.

Manage your account
===================

**Profile** in the menu **Account** shows your email addresses, your password, the linked GitHub account and your tokens; see :doc:`profile`.

Clean the cache
===============

The **Cache** page lists the repositories from the one used longest ago. Delete the ones you do not need.
