# Rules for AI agents

These rules are for AI agents (Claude Code and others) that change this
repository. People who use AI follow the [AI policy of icalendar and the Python
Calendaring Ecosystem](https://icalendar.readthedocs.io/en/latest/contribute/index.html);
see also [Contribute](https://community-insights.readthedocs.io/en/latest/contribute.html).

## Prompts and todos

- The prompts are recorded in `.prompts/` by the hook of
  [ai-prompt-auto-commit](https://github.com/PyCalendar/ai-prompt-auto-commit)
  (`.claude/settings.json`). Do not edit or delete them.
- Every prompt becomes items of `todo.txt` (markdown checkboxes): what was asked,
  in the words of the project. Mark items `- [x]` when they are done and tested.
  Before finishing, check `.prompts/` against `todo.txt`: every prompt is covered.
- Questions of the person are answered; decisions that are theirs (names,
  releases, accounts) stay open items in `todo.txt`.

## What needs confirmation

- Never run `git commit`, `git push` or `git commit --amend` unless the person
  asked for it in their own prompt. Leave changes uncommitted and say so.
- Ask and wait before anything that deletes or overwrites outside the files the
  agent made: `docker ... prune`, caches, databases, volumes, other directories.
  Information that removes an objection is not a permission.
- Check the free disk space before large downloads and builds.

## Constraints of the code

- One class per module; a module that would need more becomes a package. The
  errors are the exception: they are grouped by topic in `community_insights/errors/`.
  `tests/quality/test_structure.py` checks this.
- Errors are split up as finely as possible: one class per cause, with a title
  and a docstring that says what happened and how to solve it. They are shown
  with a link to their documentation. Do not raise a general error where a
  specific one can be defined.
- Every class and function has a docstring in the Google style (`Args:`,
  `Returns:`, `Raises:`, `Examples:`); `make lint` checks it.
- Before writing something, look for a library that does it; Django packages are
  welcome. Record what was found in the library proposals of `todo.txt`.
- Never change a migration that may be applied somewhere, also not the first one;
  add a new migration with `manage.py makemigrations`. A changed migration leaves
  databases with missing columns, such as `no such column`.
- The variables of queries are named consistently, as the command line tool
  before: a prefix of what they are about (`user_`, `commits_`, `prs_`, `issues_`,
  `comments_`, `actions_`, `activity_`) or the unit first (`hours_`, `days_`,
  `months_`); parts of a total are shown as `part/total`. docs/reference/queries.rst
  lists all of them in an alphabetical table that links to the explanation of each;
  `tests/quality/test_docs_links.py` and `tests/statistics/test_variable_names.py`
  check it.
- Pages and statistics never ask GitHub; only fetches do. The tests never use the
  network: GitHub is faked (`tests/fakes/`).
- Small classes with one responsibility, low coupling: see `docs/how-to/develop.rst`.
- JavaScript never lives in templates: no `<script>` with code, no `onclick=` or
  other event attributes, no `javascript:` links. It is in `static/js/`, loaded
  with `<script src>`, and reads what it needs from `data-` attributes (such as
  `data-confirm`). `tests/quality/test_templates.py` checks this.
- Texts people read are translated: `{% translate %}` and `{% blocktranslate %}`
  in templates, `gettext` in Python, `t()` (Django's JavaScript catalog) in
  `static/js/`. Update `locale/` with `make messages` (see
  `docs/how-to/translate.rst`).

## Tests

- Every change comes with tests, also of its edge cases and of the errors people
  can see. Tests are sorted by topic into the directories of `tests/`.
- Run what the CI runs, with the same commands: `make lint`, `make typecheck`, `make test`,
  `make test-js`, `make test-browser` (also `WINDOW=375x812`), `make check-graphql`,
  `make check-site-links`, `make check-vendor`, `make build`, `make docs`,
  `make vale`, `make linkcheck`, `make reuse`, `make zizmor`, `make docker-test`.
- Report the results as they are: say what failed and what was not run.

## Licenses and attribution

- Code, text or tests taken over from other projects keep their license and
  copyright: an SPDX header in the file and an entry in `REUSE.toml`, the license
  text in `LICENSES/`. `make reuse` checks it. Prefer writing an own version over
  copying text under another license.
- Commits written by an agent end with the attribution of the model
  (`Co-Authored-By: ...`); the prompts are added by ai-prompt-auto-commit.

## Changelog and documentation

- Every change people notice has a news fragment in `news/` without an
  extension, such as `news/+name.feature` (see `docs/contribute.rst`).
- The documentation (`docs/`) is updated with the change: how-to guides,
  reference, explanation, tutorial.
