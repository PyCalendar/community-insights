==================
Classes of people
==================

A class has a name, a colour and rules. Somebody who responded belongs to the **first** class, from the top of the list, with a rule that matches. The first response of each class counts, so a bot that answers fast does not hide the first human response.

Kinds of rules
==============

.. list-table::
   :header-rows: 1

   * - Kind
     - Value
     - Matches
   * - handles
     - space separated names
     - exactly these GitHub handles, in any case
   * - handle pattern
     - patterns with ``*`` and ``?``
     - handles such as ``*-bot``
   * - status
     - ``owner``, ``member``, ``collaborator``, ``contributor``, ``first_timer``, ``none`` ...
     - the author association GitHub reports
   * - is a bot
     - none
     - handles with ``[bot]``, Copilot and accounts of type bot
   * - location pattern
     - words
     - people whose GitHub profile location contains the word
   * - everybody
     - none
     - everyone, use as the last class

Default classes
===============

*bot*, then *collaborator or higher* (status owner, member, collaborator) and *external* (everybody else). The author of an issue or pull request never responds to their own item.
