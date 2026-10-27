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

The overview has a badge builder. Choose pull requests or issues, the percentile and optionally a class and copy the Markdown. See :doc:`../reference/badges`.

Clean the cache
===============

The **Cache** page lists the repositories from the one used longest ago. Delete the ones you do not need.
