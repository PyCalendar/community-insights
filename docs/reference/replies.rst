=======
Replies
=======

The page **Replies** (``/s/<scope>/replies/``) shows whether the authors of pull requests answered the comments and reviews they got. It helps to see who still works on their pull requests and who left them.

.. _which-pull-requests-count:

Which pull requests count
=========================

A pull request of the time range (by the day it was opened) counts for the replies of its author when all of these hold:

#. A person opened it: pull requests opened by bots are left out.
#. It was not merged. A merged pull request needs no answer any more; it only counts in **PRs merged**.
#. Its author did not close it. A pull request its author closed without merging was given up by the author: there is nothing to answer, so it does not count at all. The page of the person still lists it, marked *closed by the author: not counted*.
#. It got feedback: a response that needs a reply, a comment or a review that does not approve by somebody else than its author, and not by a bot (see :ref:`feedback`). Bots are the people of the class of bots of your :doc:`classes`, by default the accounts GitHub marks as bots. A pull request without feedback has nothing to answer.

So the pull requests that count are the open ones and those somebody else closed without merging them, each with feedback.

A pull request that counts is **replied to** when, after its first feedback, its author commented, reviewed or pushed a commit to it. A commit of somebody else, such as a maintainer who fixes the pull request, is no reply of the author. Only the last 10 commits of each pull request are read; the time of a commit is the time it was committed, which rewriting the history changes.

Who closed a pull request is read from GitHub. For a pull request read before the closers were read, it is unknown: such a closed pull request counts as closed by somebody else until it is read again.

The table
=========

Listed
   Everybody with a pull request that counts. The page says how many of all people who opened a pull request in the time range are shown, such as *6/10 contributors shown*: the others have none that counts, because theirs were merged, closed by themselves, or got no feedback but approvals.

PRs replied to
   The pull requests that count and were replied to, of all that count, such as ``1/3``.

PRs merged
   The merged pull requests of the person, of all of their pull requests in the time range, such as ``2/5``: also those that do not count.

Not replied to and open, Not replied to and closed
   The numbers of the pull requests that count and were not replied to, by repository and linked to GitHub: those still open, and those somebody else closed. Shown only for people who did not reply to everything.

PRs closed by others
   The pull requests of the person that somebody else, such as a maintainer, closed without merging them. Shown only for people who did not reply to everything.

Order
   People with an open pull request without a reply first. Then the smallest share of replies: replied to/that count, so 0/5 and 0/1 come before 1/2. With the same share, more pull requests that count come first: 0/5 before 0/1.

The badge of each person is **green** if every pull request that counts was replied to, **yellow** if the person has only one pull request, it counts, and it was not replied to, and **red** if some that count were not replied to. All badges, with the grey one of people who are not on the page, are in :ref:`reply-badges`.

The label of a row opens the replies of the person (``/s/<scope>/replies/<login>/``): all their pull requests of the time range with their titles, those without a reply first, and why the others need no reply. Every row also links to the page of the person and to their pull requests (``/s/<scope>/people/<login>/items/?kind=pr``); that page also shows their issues (``kind=issue``) or both (no ``kind``).

Pull requests read before commits and closers were read have neither: a reply by a commit is not seen there, and the page says how many there are. **Update** reads them, with what changed: it always reads all the pages need.

Badges
======

Each person has a badge: see :ref:`reply-badges` for its addresses, its colours, its JSON, and which tokens update it.

Reading what changed
====================

The page and the badges read what changed on GitHub before they show it: repositories read longer ago than ``AUTO_FETCH_AFTER_MINUTES`` get a fetch, and they wait for it at most ``AUTO_FETCH_TIMEOUT`` seconds (see :doc:`configuration`); the fetch goes on after that. A badge of a project fetches with the tokens of its owner. A public page or badge fetches with the tokens allowed for its public uses, and with the points shared for everybody (see :ref:`public-uses`); its page says so, and people who are signed in can allow one of their tokens for the badge or all badges of the scope there. Without tokens or points left, they show what is there at once. Repositories that were never read need the page *Fetch*.

Images in a README on GitHub are loaded through its image proxy, which waits only a few seconds; GitHub does not document how long, the open source Camo it is based on waits 10 seconds. So the badges wait at most ``AUTO_FETCH_BADGE_TIMEOUT`` seconds, 4 by default, and the page ``AUTO_FETCH_TIMEOUT``.

Each badge is kept for one hour (``Cache-Control: public, max-age=3600``) by browsers and the image proxy of GitHub: a README shows a new colour at most an hour later. The page of the badge says so.
