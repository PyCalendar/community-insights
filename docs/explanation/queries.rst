=====================
How queries are built
=====================

The **Contributors** page shows one row for each person who did something in the repositories. A query decides which rows are shown and how: **Who** keeps some people, **Sort by** orders them, **Group by** sums them up, **Columns** chooses what is shown, and **Chart of** what is drawn. The time range is a part of the query, too. This page explains how these parts work together and how **Who** is written. :doc:`../how-to/queries` shows the steps on the page; :doc:`../reference/query-variables` and :doc:`../reference/query-operators` list everything that can be used.

One person, one row
===================

Each variable is a number, a text or a truth value of one person in the time range: ``prs_total`` is how many pull requests they opened, ``user_location`` where they say they live, ``user_bot`` whether they are a bot. **Who** is a condition that is checked for every row: a person is shown when it is true.

The time range comes first. It decides what is counted at all: with the last 30 days, ``prs_total`` counts the pull requests of the last 30 days, and ``days_last < 60`` is always true for the people shown. Choose the time range for the question, then write **Who** for the people.

A condition step by step
========================

The simplest condition compares one variable with a value:

.. code-block:: text

    prs_total > 3

Numbers are compared with ``==``, ``!=``, ``<``, ``<=``, ``>`` and ``>=``. Text is written in quotes and compared in any case with ``==``, ``!=``, ``in`` and ``not in``:

.. code-block:: text

    user_class == "external"
    "berlin" in user_location

A variable that is true or false stands alone:

.. code-block:: text

    user_bot
    not user_bot

Conditions are combined with ``and`` (both must be true) and ``or`` (one is enough). ``not`` turns a condition around. ``not`` binds closest, then ``and``, then ``or``; parentheses make another order clear:

.. code-block:: text

    not user_bot and (prs_total > 3 or prs_reviewed > 3)

A chain of comparisons keeps a value in a range: ``1 <= issues_opened < 10``.

An example, piece by piece
--------------------------

Who contributed continuously in the last two months, but is new to the project? With the last 60 days as the time range:

.. code-block:: text

    days_last < 60 and not user_bot and prs_total > 3 and commits_total < 300 and prs_reviewed < 1

- ``days_last < 60``: still active.
- ``not user_bot``: a person.
- ``prs_total > 3``: more than three pull requests in the two months, so continuously.
- ``commits_total < 300``: not one of the people with many commits.
- ``prs_reviewed < 1``: does not review yet, as the established people do.

Sorted by ``-prs_total``, the most active of them come first.

How a query is read
===================

The text of **Who** is read like an expression of Python, but it is never run. Only names of variables, numbers, text in quotes, ``True``, ``False``, comparisons, ``and``, ``or``, ``not`` and parentheses are accepted; anything else is refused with an error that says what is wrong and links here. So a query cannot do anything on the server but compare the numbers of the people.

Some values are not known: a person who never responded has no ``hours_to_respond``. Such values are infinite: they are bigger than any number, so ``hours_to_respond < 24`` leaves them out, and they come last when sorted by the smallest first. The table shows them as ``-``.

Names that belong together
==========================

The names of the variables are built the same way: a prefix of what they are about, such as ``user_``, ``prs_`` and ``issues_``, or the unit first, such as ``days_`` and ``hours_``. So ``prs_merged``, ``prs_unmerged`` and ``prs_open`` are parts of ``prs_total``, and the table shows them as ``3/5``: three of five. Typing the start of a prefix in **Who** lists the variables that start with it.

Sort, group and keep
====================

**Sort by** takes a variable, with ``-`` in front for the biggest first. **Group by** sums the numbers of the people with the same value, such as all people of a country: the rows are then groups, and **Who** still decides who is counted. A query, with its time range, can be saved under a name and opened again, and its address can be shared: it shows the same result to everybody who may see the repositories.
