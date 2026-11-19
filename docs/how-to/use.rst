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

The pages of a project
======================

The drop-down at the top of every page of a project, and the menu of its card on the dashboard and on **Explore**, lead to the same pages:

- **Overview**: how many pull requests and issues are open, merged and closed, how many people contributed, by class of people, and the five most active people who are not bots. It loads fast: the response times have their own page.
- **Response times**: how long pull requests and issues waited for their first response.
- **Trends**: whether more or fewer issues and pull requests are opened and closed, with the contributions and the new contributors, next to the time before, and whether the contributions really grow.
- **Countries**: a map of the world with the countries of the contributors.
- **Languages**: which languages the contributors likely speak, from their countries.
- **Contributors**: everybody who contributed, chosen and sorted with a query.
- **Pull requests and issues**: all of them, with their state in the colours of GitHub (green open, red closed, purple merged) and their first response; *waiting* marks the open ones that no collaborator or higher has answered yet, and a merge counts as a response (see :doc:`../explanation/responses`). Kind, state and whether somebody responded are multiple choices: all are chosen at first, so choose for example *closed* and *merged* together.
- **Replies**: who replied to the feedback on their pull requests.
- **Badges**: the badges to put into a README.
- **Compare repositories**, for several repositories.

The pages of a person have their own drop-down in the path at the top: their **Contributions**, their **Replies**, their **Pull requests and issues**, and their **Badges**.

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

The page **Response times** shows, for pull requests and for issues:

- the bars of the times until the first response of each class; point at a bar to see its numbers,
- the curve of the share still waiting for a response (Kaplan-Meier),
- the table of one statistic: **Statistic** chooses *measured*, *normal*, *exponential* or *Kaplan-Meier*, at first the one with the lowest standard error,
- the trend: whether the first responses get faster or slower per month.

:doc:`../explanation/response-times` explains how to read each of them.

Read the trends
===============

The page **Trends** shows issues on the left and pull requests on the right, on a phone one below the other:

#. Choose **Last 7 days**, **Last 30 days** or **Last 90 days** at the top, or **From** and **To** for other dates.
#. Each card shows a number of the time range and how it changed from the time just before: *opened*, *closed* (for pull requests *merged* and *closed without merging*), *contributions* with how many people made them, and *new contributors*.
#. The charts show the same per day, calendar week, month or year; point at a bar to see its number. **Bars of the charts** chooses the length of the bars; **automatic** chooses it by the time range.
#. **Statistical trend** says how much the contributions and the contributors grow or shrink per day, week or month, how exact that is, and whether it is statistically significant.
#. Below, the new contributors are listed by their handle; a name opens the page of the person.

:doc:`../explanation/trends` explains what is counted and how the trend is computed.

See where the contributors are from
===================================

#. Open **Countries** in the drop-down of the pages of a project. The top says how many contributors of the time range have a location with a known country, such as *12/20 contributors mapped*.
#. Point at a country on the map to see how many contributors are from it. Scroll or pinch to zoom, and drag to move the map; small countries have a dot.
#. Click a country, or its name in the list, to see its contributors, their locations, their first and last contribution, and its official languages below the map. The address ends with ``#country=`` and the code of the country, so it can be shared.
#. Open **Languages** for an estimate of the languages, ranked by the contributors, with the countries each comes from.

:doc:`../explanation/countries` explains how locations become countries and languages.

Who replies to feedback
=======================

**Replies** shows whether the authors of pull requests replied to the comments and reviews they got, with a coloured label for each person; the label opens the replies of the person, with all their pull requests and their badge. :doc:`../tutorials/replies` goes through it step by step, and :doc:`../reference/replies` explains which pull requests count. The page and the badges read what changed on GitHub first, a few seconds at most.

Badges
======

The page **Badges** has the builder of the badge of the response time: choose pull requests or issues, the percentile, optionally a class, the statistic, the text of the left side and SVG or PNG, and copy the code for Markdown, reStructuredText, HTML or the plain URL. Each person on **Replies** has a badge of their replies, with its own page and code. Every badge is also JSON. :doc:`../reference/badges` lists the badges and their colours.

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
