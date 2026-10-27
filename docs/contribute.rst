==========
Contribute
==========

Set up the :doc:`development environment <how-to/develop>`, then:

* ``make test`` runs the tests, ``make lint`` the style check; the pre-commit hooks run ruff.
* Describe user visible changes in a news fragment: a file ``news/<issue number>.<type>`` without extension, such as ``news/42.feature``, where the type is ``breaking``, ``feature``, ``bugfix``, ``documentation`` or ``misc``. Without an issue use ``+name.<type>``. Pull requests without a fragment fail the check unless they have the label ``skip-changelog``.
* ``todo.txt`` lists what is done and open.

Project constraints
===================

* Errors are split up as finely as possible: one class per cause in ``community_insights/errors/``, each with a docstring that says what happened and how to solve it. Then each has its own entry in :doc:`reference/errors` and can be caught specifically. Do not raise a general error where a specific one can be defined.
* All classes and functions have a docstring in the `Google style <https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings>`_: a summary line, a blank line, the description, and the sections ``Args:``, ``Returns:``, ``Raises:`` and ``Examples:`` where they apply. ``make lint`` checks it with ruff. ``tests/test_docstrings.py`` allows only these headings and lists the docstrings that still lack a section as expected failures; ``tests/test_with_doctest.py`` runs the examples (``>>>``) of the code and of the documentation. Both are adapted from icalendar (BSD-2-Clause).
* One class per module (see :doc:`how-to/develop`).

AI contributions
================

You may use AI to contribute. Follow the `AI policy of icalendar and the Python Calendaring Ecosystem <https://icalendar.readthedocs.io/en/latest/contribute/index.html>`_: say which model you used and how, take responsibility for the result, and make sure nothing is copied from sources you may not use. The ``ai-prompt-auto-commit`` pre-commit hook records the prompts and adds them to the commits.

AI agents that work in this repository follow `AGENTS.md <https://github.com/PyCalendar/community-insights/blob/main/AGENTS.md>`_ (Claude Code reads it through ``CLAUDE.md``): every prompt becomes items of ``todo.txt``, nothing is committed or deleted without asking, and the project constraints above apply.
