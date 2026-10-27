.. _query-operators:

===============
Query operators
===============

The field **Who** of the contributors page holds an expression that is true for the people to show; empty means everybody. These are all the parts an expression can have. The names it compares are in :doc:`query-variables`; :doc:`../explanation/queries` explains how to build one.

Comparisons
===========

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Operator
     - For
     - True when
   * - ``==``
     - numbers, text, ``True``, ``False``
     - both sides are equal; text in any case: ``user_class == "Bot"`` matches *bot*
   * - ``!=``
     - numbers, text, ``True``, ``False``
     - both sides differ
   * - ``<``, ``<=``
     - numbers
     - the left side is smaller, or at most as big
   * - ``>``, ``>=``
     - numbers
     - the left side is bigger, or at least as big
   * - ``in``
     - text
     - the text on the left is a part of the one on the right, in any case: ``"berlin" in user_location``
   * - ``not in``
     - text
     - the text on the left is no part of the one on the right

Comparisons can be chained: ``1 <= issues_opened < 10`` is true when both comparisons are.

Combinations
============

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Operator
     - True when
   * - ``not A``
     - A is false
   * - ``A and B``
     - both are true
   * - ``A or B``
     - one of them, or both, are true
   * - ``( )``
     - groups a part: ``user_bot or (prs_total > 0 and days_last < 30)``

``not`` binds closest, then ``and``, then ``or``: ``A or B and not C`` means ``A or (B and (not C))``. A variable of the kind *bool*, such as ``user_bot``, is true or false on its own: ``not user_bot`` needs no comparison.

Values
======

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Value
     - Meaning
   * - ``"text"``, ``'text'``
     - text, in double or single quotes
   * - ``12``, ``2.5``, ``-1``
     - numbers; a minus in front makes them negative
   * - ``True``, ``False``
     - truth values, to compare with ``==`` or ``!=``

Not possible
============

A query is read as a Python expression but never run: only the parts above are accepted. Calculations such as ``prs_total - prs_merged``, functions, ``is``, and text compared with ``<`` or ``>`` give an error that says what is wrong, see :doc:`queries`.

Examples
========

.. code-block:: text

    prs_merged >= 2 and days_last < 90 and not user_bot
    "berlin" in user_location or user_class == "maintainers"
    user_country == "DE" and user_horizon_europe
    hours_to_respond < 24 and prs_reviewed > 10
