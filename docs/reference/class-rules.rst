==============
Kinds of rules
==============

A class of people has rules: somebody belongs to the class when one of its rules matches. The classes are checked from the top of the page **Classes**, and the first class with a matching rule wins, so specific classes go above general ones. :doc:`classes` explains the classes; this page lists the kinds of rules, what their value is and what they match. The page **Classes** links each rule here.

.. list-table::
   :header-rows: 1
   :widths: 35 25 40

   * - Kind of rule
     - Value
     - Matches
   * - :ref:`everybody <rule-any>`
     - none
     - Everybody: the rule always matches.
   * - :ref:`handle pattern (* and ?) <rule-pattern>`
     - patterns, separated by spaces; ``*`` and ``?``
     - Handles that fit one of the patterns, in any case: ``*`` stands for any text and ``?`` for one character.
   * - :ref:`handles (space separated names) <rule-handle>`
     - handles, separated by spaces or commas
     - Exactly these GitHub handles, in any case.
   * - :ref:`is a bot <rule-bot>`
     - none
     - Accounts GitHub marks as bots, such as ``dependabot[bot]``.
   * - :ref:`location pattern (* and ?) <rule-location>`
     - words, ``*`` and ``?`` allowed
     - People whose location in their GitHub profile contains one of the words, in any case; ``*`` stands for any text and ``?`` for one character.
   * - :ref:`status (owner, member, collaborator, contributor, ...) <rule-association>`
     - statuses, separated by spaces
     - The status the person has in the repository, as GitHub tells it with each comment and review: ``owner``, ``member``, ``collaborator``, ``contributor``, ``first_timer``, ``first_time_contributor``, ``mannequin`` or ``none``.

.. _rule-any:

everybody
---------

Value: none.

Everybody: the rule always matches. Put the class with it last; it catches whoever no class above took, as the class *external* does.

Examples of the value:

.. code-block:: text

    (no value)

.. _rule-pattern:

handle pattern (* and ?)
------------------------

Value: patterns, separated by spaces; ``*`` and ``?``.

Handles that fit one of the patterns, in any case: ``*`` stands for any text and ``?`` for one character. Use it for families of accounts, such as bots named alike.

Examples of the value:

.. code-block:: text

    *-bot renovate*
    team-??

.. _rule-handle:

handles (space separated names)
-------------------------------

Value: handles, separated by spaces or commas.

Exactly these GitHub handles, in any case. Use it for the people you know, such as the maintainers of a project.

Examples of the value:

.. code-block:: text

    alice bob
    kim, sam

.. _rule-bot:

is a bot
--------

Value: none.

Accounts GitHub marks as bots, such as ``dependabot[bot]``. Some bots use an account like that of a person and are not marked; add their handles to the class with a rule *handles*, as the class *bot* does with ``coveralls``, or use the suggestions on the page **Classes**.

Examples of the value:

.. code-block:: text

    (no value)

.. _rule-location:

location pattern (* and ?)
--------------------------

Value: words, ``*`` and ``?`` allowed.

People whose location in their GitHub profile contains one of the words, in any case; ``*`` stands for any text and ``?`` for one character. People without a location never match. The location is what people wrote, so it can be wrong or old.

Examples of the value:

.. code-block:: text

    berlin munich
    germany deutschland

.. _rule-association:

status (owner, member, collaborator, contributor, ...)
------------------------------------------------------

Value: statuses, separated by spaces.

The status the person has in the repository, as GitHub tells it with each comment and review: ``owner``, ``member``, ``collaborator``, ``contributor``, ``first_timer``, ``first_time_contributor``, ``mannequin`` or ``none``. The rule matches when the status is one of the words, in any case. Use it to tell the people who look after a project from those who contribute.

Examples of the value:

.. code-block:: text

    owner member collaborator
    first_timer first_time_contributor
