================
Manage the users
================

Administrators see the users of the site and choose who else is an administrator. The first administrator is added as described in :ref:`configure-administrator`.

See the users
=============

Open **Users** in the menu **Account**. The section above **Sign out** with **Cache**, **Admin** and **Users** is only shown to administrators.

The table lists every account: its name, its email address, the handle of the linked GitHub account, the day it joined, and whether it is an administrator. *not linked* means the person signed up with an email address and has not linked a GitHub account yet.

Make somebody an administrator
==============================

Press **Make admin** in the row of the person and confirm. An administrator can see and change all data of the site: the cache, every table in **Admin**, and this page.

Remove the administrator access
===============================

Press **Remove admin** in the row of the person and confirm.

You cannot remove your own access, so that the site always keeps an administrator. Ask another administrator to do it.

.. vale off

The page shows the error :class:`~community_insights.errors.users.CannotRemoveOwnAdminAccess` then.

.. vale on
