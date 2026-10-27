========
Security
========

Report a vulnerability privately with a `security advisory <https://github.com/PyCalendar/community-insights/security/advisories/new>`_, not in a public issue. Say what can be done, how, and which version you used; the version is on the **About** page.

What the site keeps safe
========================

* GitHub tokens are stored encrypted (``SALT_KEY`` and ``SECRET_KEY``, see :doc:`reference/configuration`).
* Pages and statistics never call GitHub; only fetches the person started do, with their tokens and the points they share.
* Badges contain a secret token of the project and no GitHub token.
* Without ``DEBUG``, errors show what happened and what to do, no stack traces.
