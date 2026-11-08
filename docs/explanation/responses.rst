===================
What a response is
===================

Every page of the site answers the same question in the same way: did somebody respond to a pull request or an issue, and when? This page is the one definition of a response that the pages share. In the code it is ``responses_to`` in ``community_insights/stats/responses.py``; the pages only choose among the responses it finds.

.. _response-definition:

A response
==========

A response is something that somebody other than the author does to the pull request or issue:

- a **comment**,
- a **review**, in any state, also one that approves,
- the **merge** of a pull request, at the time it was merged,
- the **close** of a pull request or issue, at the time it was closed.

These are no response:

- what the author does, also closing their own pull request or issue: the author gave up, nobody answered;
- opening it, and commits.

The time of a response is from the creation of the item until the response.

Who merged or closed an item is read from GitHub (see :doc:`pipeline`). For an item read before the closers were read it is unknown: its close is no response until **Update** reads it again. The status of who merged or closed it is the most privileged status of their comments and reviews in the repository; without any, it is *collaborator*, because only people who maintain the repository can merge or close the items of others.

.. _first-response:

The first response
==================

The **first response** of an item is its first response that is not of a bot. Bots are the people of the first class with the rule *is a bot* (see :doc:`../reference/classes`); the default class *bot* has this rule, so the accounts GitHub marks as bots are bots. If none of your classes has this rule, nobody is a bot. Without classes of people, the accounts GitHub marks as bots are bots.

The first response of each **class of people** is the first response of somebody of the class. The first response of a bot does not hide the first response of a maintainer: each class has its own.

.. _waiting:

Waiting
=======

An item **waits** while it is open and nobody of the status collaborator or higher (owner, member or collaborator), and not a bot, has responded. A response of somebody else, such as another contributor, is a first response, but the item still waits for a collaborator. A closed item waits no more.

.. _feedback:

Feedback
========

The page **Replies** asks the other way round: did the author answer the responses they got? **Feedback** is a response that needs a reply of the author: a comment, or a review that does not approve, and not of a bot. A merge or a close ends the conversation and an approval asks for nothing, so they are no feedback. See :doc:`../reference/replies`.

Where the pages use it
======================

.. list-table::
   :header-rows: 1

   * - Page
     - What it shows of the responses
   * - **Pull requests and issues**
     - the first response of each item, *waiting* for open items that wait, *no response* for closed items without one
   * - **Response times**, the **Badges** of response times, **Compare repositories**, the dashboard
     - the first response of each class of people; without a class, the first response of the item
   * - **Contributors**
     - ``hours_to_respond``: the median time until the first response of the person on each item of others
   * - the page of a person
     - their first response on each item of others, by month
   * - **Replies** and its badges
     - the feedback
   * - the downloads
     - ``seconds_any``: the first response of the item; ``seconds_<class>``: that of each class
