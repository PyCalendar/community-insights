===================
Translate the pages
===================

The pages are in English and German. People get the language of their browser; the names of the languages at the bottom of every page switch it, and the choice is kept in a cookie. The addresses stay the same in every language, so links and badges keep working.

What is translated
==================

- The templates in ``community_insights/templates/``: texts are in ``{% translate %}`` and ``{% blocktranslate %}``.
- Texts of Python code that people see, such as the messages after a form and the titles of the errors: ``gettext`` and ``gettext_lazy``.
- The texts the JavaScript in ``static/js/`` writes into the page: ``_("...")``, from `Django's JavaScript catalog <https://docs.djangoproject.com/en/stable/topics/i18n/translation/#using-the-javascript-translation-catalog>`_ at ``/jsi18n/``. In node, ``_`` returns the English text, so the tests of the JavaScript need no catalog.

The details of the errors, the names of the variables of queries, the charts and the exported files are in English.

Change or add a text
====================

1. Install `GNU gettext <https://www.gnu.org/software/gettext/>`_, for example ``sudo apt install gettext``.
2. Mark the new text in the template, the Python code or the JavaScript as above.
3. Update the catalogs and compile them:

   .. code-block:: bash

       make messages

4. Translate the new entries in ``locale/de/LC_MESSAGES/django.po`` and ``djangojs.po``, for example with `Poedit <https://poedit.com/>`_ or a text editor. Remove the ``fuzzy`` mark of entries you checked.
5. Compile again and check the catalogs:

   .. code-block:: bash

       make test-translations

The tests in ``tests/i18n/`` fail if a text has no translation, if a translation lost a placeholder such as ``%(name)s`` or an HTML tag, or if the compiled ``.mo`` files are older than the ``.po`` files. The CI runs ``make test-translations``.

The German texts address people informally, with a capital letter as in a letter: *Du*, *Dir*, *Dein*.

Add a language
==============

1. Add the language to ``LANGUAGES`` in ``community_insights/settings.py``, such as ``("fr", "Français")``.
2. Create its catalogs: ``make messages LANGUAGES="de fr"``, and add it to ``LANGUAGES ?=`` in the ``Makefile``.
3. Translate ``locale/fr/LC_MESSAGES/*.po`` and run ``make test-translations``.
