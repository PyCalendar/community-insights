.. _change-log:

=========
Changelog
=========

Changes are collected as small files in `news/ <https://github.com/PyCalendar/community-insights/tree/main/news>`_, where the changes not released yet can be read, and joined into this page when a version is released (see :doc:`release`). The newest changes are listed first.

.. towncrier release notes start

0.1.0 (2026-11-03)
------------------

Breaking changes
~~~~~~~~~~~~~~~~

- ``DEFAULT_SUPERUSER`` is an email address and a password, such as ``admin@example.com:a-long-password``, applied each time the site starts; the form ``name:password`` stops the start.
- Rebuild the project as a Django web application: sign in with GitHub, dashboard, statistics, response time badges. The command line tool before the rewrite is removed; it is in the git history.
- The project is called Contributor Community Insights; the package is ``community-insights``.
- The variables of queries have the names of the command line tool before, grouped by prefix: such as ``user_handle``, ``prs_total``, ``comments_total``, ``hours_to_respond``. More are back: ``commits_total``, ``prs_unmerged``, ``prs_commented``, ``prs_reviewed``, ``issues_commented``, ``user_association``, ``actions_merges``, ``days_to_merge``. Saved queries are renamed; an old name in a query says its new one.


New features
~~~~~~~~~~~~

- A badge can use any statistic of the overview, chosen with ``model``: measured, normal, exponential or Kaplan-Meier; the badge builder has the same choice.
- A page lists the pull requests, issues or both of one person in the repositories of a page (``/s/<scope>/people/<login>/items/``).
- A shared statistic carries the classes of people it was made with: each class has an id such as ``maintainer-3``, and the addresses name them with ``classes`` when they differ from the default ones.
- A web process starts with about 85 MB instead of 290 MB: the libraries of the statistics and charts are loaded when a page first needs them.
- Add SVG badges for the response time at a chosen percentile.
- Add a Docker image for gunicorn that is published to the GitHub container registry.
- Add a dashboard for public and private projects, whole organisations, and views of several projects.
- Add an About page with the version and the licenses of all packages, and a footer with a link to report bugs.
- Add contributor tables and per-person activity charts in the time zone of the browser.
- Add response time statistics and charts with configurable classes of people.
- Badges are drawn by ``anybadge``, which measures the text, and screen readers read them as one image named by their label and value.
- Charts, their data and badges are kept until the data changes, with an ``ETag``: a browser that has the image gets ``304 Not Modified``. The contributors are computed once per change of the data, and looking at a page no longer writes to the database, so the contributors page of collective/icalendar loads in 0.4 instead of 10 seconds.
- Classes of people are moved by drag and drop, and their name and colour are changed in place.
- Classes, tokens and the columns of the contributors table are moved by drag and drop with Sortable.js, also on phones; tokens can now be dragged too.
- Download the data behind every statistic as CSV or JSON; the fits are made with scipy.
- Each account may keep a number of pull requests and issues in its projects (``USER_MAX_ITEMS``, administrators have no limit); the fetch page shows how many are held.
- Every badge is also a PNG and JSON (badge.png, badge.json); the JSON has the spec of shields.io endpoint badges and what the badge counted, for the reply badges the row of the table. The pages that make badges switch between SVG and PNG and link the JSON.
- Every error links to the page of the documentation that explains its topic, such as tokens, classes or queries, next to *What to do*.
- Fetches read the last commits of each pull request and who closed it.
- GitHub access has the buttons "Token for a month" and "Token for a year": they open the form of GitHub for a new token, filled in for this site.
- Keep what is read from GitHub in the database, with the time of last use, a cache page and ``clear_cache``.
- Mail servers on port 465, such as smtp.zoho.com, work: ``EMAIL_USE_SSL`` is read and chosen for that port. Both ``EMAIL_USE_SSL`` and ``EMAIL_USE_TLS`` set to true stop the start with an error.
- More is translated: the details of errors, the descriptions of the query variables and the texts in the charts.
- ODS files are made in the background with a progress bar instead of timing out, and wait a week for the download. Accounts have messages, read and unread: a finished file sends one.
- On a desktop, the heading of a table sticks to the top of the window while the page scrolls.
- On the page of a person, the numbers of pull requests and issues lead to their lists.
- Only administrators see the cache page; pages without access, missing pages and server errors have the look of the site.
- Query the contributors, filter every page by time, list pull requests and issues, compare repositories.
- Read GitHub asynchronously and concurrently within its secondary rate limits; continue stopped fetches.
- Read GitHub in background jobs with a queue, priorities, cancelling, an estimate of the API points and time, and a Downloads page.
- Read from GitHub reads at once, the same on every page and on the cards of the dashboard and of Explore, and always all the pages need: also the commits and closers of pull requests read before these were read. Its drop-down opens the page Fetch to choose what and how much is read.
- Read public repositories without a token, with the quota of the server.
- Running a query, with Enter or the button, scrolls the page so that the query is at the top and its result below it.
- Share points of tokens with everybody on the site, with two sliders per token; ask for more points when they are not enough.
- Share the statistics: **Share** copies the address of a statistics page, and **Share this chart** gives the code of a chart for Markdown, reStructuredText, HTML or as a link, linked to the page it comes from. The badge builder gives the same four formats, and the left side of a badge can be chosen with ``label``.
- Shared addresses open without a sign in: **Share**, **Share this chart** and the link of a badge name the public repositories of a project instead of the project, with the time range, the query and the classes of people, so others see the same page.
- Show errors with what they mean and a link to their description in the documentation.
- Show on every statistics page how complete the data is, its sources, and choose or add sources.
- Sign up with an email address; GitHub can be linked later.
- Switch between a light, a dark and an automatic theme; the charts use the colours of the page.
- The About page links the license of each Python package to its text, read by pip-licenses.
- The About page lists the code taken over from other projects, with its copyright and license, from REUSE.toml.
- The button *Read from GitHub* is named *Update*.
- The charts are easier to read: the bars of the classes stand side by side, the response times per month show durations such as 6h or 1d from 0, the times of the day and the counts have units, and the heat map goes from dark to the full green without white.
- The charts of the overview, of a person and of a query are interactive, with hints over the points, drawn by Chart.js; the SVG stays for sharing.
- The classes of people the site makes are hidden instead of deleted, still sorting people, and link to an explanation of what they are for; the kinds of rules have a reference page linked from each rule.
- The colours of the page are chosen from a menu behind one button with an icon, like in the documentation.
- The columns of the contributors table sort it with a click on their name, link to their explanation, and can be named in words instead of as variables.
- The contributors page helps with queries: the names of the variables are completed while typing, Enter runs the query, the columns are moved by drag and drop or arrows and added from a list, and a link leads to the documentation of queries, as do the errors of queries.
- The contributors table shows ``hours_to_respond`` as a time, such as 2d 4h or 3h 12min; queries still compare hours. The column titles in words start without *the*, and *pull requests opened and merged* is *pull requests merged* (also closed and still open).
- The country of the locations of people: the query variable ``country``, grouping by country, and a tag next to the locations in the countries of Horizon Europe, chosen in the profile.
- The footer shows the version without the commit, such as "Version 0.0.1.dev8"; the page About has the commit.
- The image starts one gunicorn worker instead of two (``WORKERS=1``): each one needs about 300 MB, so the container fits into 600 MB. Set ``WORKERS=2`` for more at once.
- The limits of visitors per address are counted by ``django-ratelimit``.
- The made up demo project disappears from Explore when there are other repositories, and the test of a token skips it.
- The overview draws the Kaplan-Meier curve of each class: the share of the items still waiting for a response, with its confidence band.
- The overview says whether the first responses get faster or slower per month, with its p-value.
- The page Profile shows the email addresses, the password, the linked GitHub account and the tokens of an account, with the pages to change them.
- The page Replies and its badges read what changed on GitHub before they show it, waiting at most ``AUTO_FETCH_TIMEOUT`` seconds (10 by default), with the tokens of the owner of the project or the shared ones; without points left they do not wait.
- The page Replies shows whether the authors of pull requests replied to the comments and reviews they got. Merged pull requests, those their author closed and approvals need no reply. For each person: a green, yellow or red badge, the pull requests replied to and merged as X/Y, those without reply by repository (open and closed), and those somebody else closed. The table can be sorted by dragging its columns into an order; people with an open pull request without reply come first. The page says how many contributors it shows of all.
- The pages are translated: English and German, chosen by the browser or with the switch at the bottom of every page. See "Translate the pages" in the documentation to add or change texts.
- The pages use the width of the window up to 1400 pixels, so that tables fit; on phones the cards are thinner, and the page Replies shows the badge above the shortened handle.
- The progress of fetches and files, and the queries of the contributors page, update without loading the page again (htmx).
- The replies of one person (``/s/<scope>/replies/<login>/``) list all their pull requests with their titles, those without reply first, and why the others need none; the badge links to this page, and its page has the code to copy it.
- The reply badges wait at most ``AUTO_FETCH_BADGE_TIMEOUT`` seconds (4) for a fetch, as GitHub's image proxy waits only seconds, and are kept for an hour.
- The requests to GitHub are sent with httpx, at an even pace kept by aiolimiter.
- The site has the icon of pycal.org in the tab of the browser.
- The site is in Spanish, too; the language is chosen in a drop-down at the bottom of every page.
- The suggested limit of API points in the profile is also the number above which a fetch asks for a limit.
- The table of the response times shows one statistic at a time, chosen with **Statistic**; the one with the lowest standard error comes first. The table explains why Kaplan-Meier counts all items.
- The tables behind the statistics can be downloaded as Parquet, with numbers and times as types.
- The time range (From, To, the last days) is below the data and its button *Update*.
- The time range is a part of a query: **Or the last days** moves with the days, the example queries set their own time range, and saved queries keep theirs.
- The type hints are checked with pyright and ``django-types``: ``make typecheck``, also in the CI.
- The version comes from the git tag of the release, read by hatch-vcs, instead of being written in pyproject.toml.
- Tokens have public uses: besides everybody on this site, a token can be allowed for the badges of replies (all of a scope or one person's), the public pages, or the fetches of visitors of a public scope, each with its own share of the points per hour, listed, changed and removed under GitHub access. The page of a badge adds one for the badge or all badges of its scope. The share of a token for everybody becomes its public use "everybody on this site" (a migration).
- Use several GitHub tokens in order, each with an hourly limit; test them on all projects; warn about tokens that never expire.
- Visitors without an account may add and read only some repositories per address and hour (``VISITOR_SUBMITS_PER_HOUR``, ``VISITOR_FETCHES_PER_HOUR``), so nobody uses up the donated tokens alone. ``TRUSTED_PROXIES`` tells the site how many proxies are in front of it.
- coveralls counts as a bot, and the page **Classes** suggests accounts that answer like bots, mostly within 2 minutes, to add them with one button.


Bug fixes
~~~~~~~~~

- A fetch no longer stops when GitHub answers a query with a server error (502, 504) or something unreadable, as when a query took it too long: the request is tried again, 1, 2 and 4 seconds later.
- A private repository that only a token shared by someone else, or donated to the site, can see is not found, as if it did not exist: the site no longer tells that it is private, and does not add it to a project.
- The GraphQL queries are validated against the schema GitHub publishes; the query of your own repositories no longer declares an unused variable.
- The container is healthy with ``ALLOWED_HOSTS`` set: its health check sent the host 127.0.0.1, which Django refused with 400, so Docker and Sencho saw it unhealthy.
- The container starts faster: the steps before it serves run in one process (``manage.py prepare``), and failed health checks while it starts no longer make it unhealthy, so a deploy that waits for a healthy container does not fail.
- The contributors table shows the total of prs_merged, prs_unmerged, prs_closed and prs_open again, such as 3/5, also when prs_total is no column.
- The documentation builds on Read the Docs again: the package is built with hatchling and contains only ``community_insights``.
- The list of pull requests and issues no longer shows the comment of a bot, such as github-actions, as the first response: the first comment or review of a person counts, as in the statistics.
- The pages to sign up, sign in and manage the account have the look of the site again.
- The query field suggests the names of the variables also for what was typed while the page was still loading.


Documentation
~~~~~~~~~~~~~

- A new page explains how to read the response times: what measured, normal, exponential and Kaplan-Meier show, what each column means and which statistic to trust; the overview links to it.
- A reference page lists every variable, operator, group and error of queries; the errors of queries link to it.
- Add a tutorial to set up an installation with Docker Compose, with the optional steps.
- New pages for queries: all variables in an alphabetical table with an explanation of each, all operators, and how queries are built; the column headers of the contributors table link to their variable.
- The changelog links to news/ on the main branch, where the changes not released yet can be read.
- The documentation has ``make livehtml`` to see it while editing, ``make linkcheck`` for its links, and ``make vale`` without an own installation of Vale. The CI checks the links and the prose; broken links of the documentation are fixed.
- The guide to tokens walks through GitHub's form step by step, with an example, and explains API points and limits; the page GitHub access links to it.
- The links point to the repository at https://github.com/PyCalendar/community-insights.
- The links to the documentation lead to its latest version.
- ``.env.example`` lists every configuration variable in sections, each with an explanation and its default; the configuration reference adds ``PRIVATE_REPOSITORIES``, ``SOURCE_URL`` and ``DOCS_URL``.


Maintenance
~~~~~~~~~~~

- A test runs the fetch worker in a process of its own and fails when it imports a package that is not on its list, such as pandas or matplotlib, so the worker stays small next to gunicorn.
- No JavaScript in the templates any more: confirmations use ``data-confirm`` and ``static/js/confirm.js``, and the time zone is sent by ``static/js/time-zone.js`` instead of the inline script of ``django-tz-detect``. The page title of *GitHub access* no longer shows a script tag.
- One Python package: the code of the app ``community`` is now in ``community_insights``, next to the settings. The tables and the migrations keep their names, so existing databases work as before.
- Test the JavaScript with node, the website in Firefox with behave, and every page and link with a crawler.
- The CI scans the image with Trivy (``make docker-scan``) before it is pushed: critical vulnerabilities that have a fix stop it.
- The browser tests run with pytest and Playwright instead of behave and selenium.
- ``make benchmark`` measures how fast each page and image of a project loads again, and how much memory each request needs.
- ``make run`` runs the fetch worker, too, and creates the superuser admin; ``make run`` and ``make docker-run`` share the database.
- make check-site-links checks every link of the running site with LinkChecker, and make check-vendor checks that static/vendor comes from package-lock.json; both run in the CI.
