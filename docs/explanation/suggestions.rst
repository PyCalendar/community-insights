===========
Suggestions
===========

On GitHub, a reviewer can suggest code: a review comment with a block of suggested code that the author can apply with one click. The pages **Suggestions** show for each pull request which suggestions were applied, which are open, and which are unknown, and the badges sum it up. This page explains how a suggestion is found and how its status is decided.

What a suggestion is
====================

A suggestion is a review comment, a comment on lines of the code of a pull request, that contains a block of suggested code, written as

.. code-block:: markdown

    ```suggestion
    the new lines
    ```

A comment in the conversation of the pull request, or a review comment without such a block, is no suggestion, even when it suggests something in words.

The status of a suggestion
==========================

Each suggestion has one of three statuses. The first rule that holds decides:

applied
    #. **Committed from GitHub.** The author used **Commit suggestion** or **Add suggestion to batch**: GitHub makes a commit named *Apply suggestion…* or *Apply suggestions from code review*, with the suggester as an author or co-author. A suggestion counts as committed this way when such a commit came after it, has its suggester as an author, and the lines of the suggestion changed since: GitHub then marks the comment as outdated.
    #. **A reply names a commit.** A later comment in the thread names a commit by its hash, such as ``3f2c9ab``, or by its address. This is how people say that they applied a suggestion by hand: *done in 3f2c9ab*.
    #. **Resolved by the suggester.** The person who suggested the code resolved the thread: they are content.
unknown
    #. **Resolved by somebody else.** The author or a third person resolved the thread without a commit named in it. The suggestion may have been applied, or turned down: resolving a thread is a click that says the conversation is over, not that the code changed. GitHub records no link between a resolved thread and a commit, so the site cannot tell the two apart from the thread alone.
    #. **Answered with another suggestion.** A later comment in the thread suggests other code. The new suggestion counts on its own.
open
    Anything else: the suggestion is not applied yet.

The pages also show why a suggestion has its status, such as *a reply names a commit*. When the thread was resolved, the column **Resolved by** names who resolved it, by their handle, instead: *unknown* and the handle of the author for a thread the author resolved.

**Last in the thread** names who of the author of the pull request and the suggester wrote last in the thread of the suggestion, by their handle, and links to that message. Others who wrote in the thread do not count: the question is whose turn it is.

How the suggestions are read
============================

The suggestions are read from GitHub with the fetch of a repository: all review threads of each pull request that got a review, all comments of each thread, and all commits of the pull request. The first request asks for 10 pull requests at a time with their first 50 threads, the first 20 comments of each thread and the first 100 commits; whatever does not fit is read in further pages of 100 until nothing is left. The authors and co-authors are read only of the commits named *Apply suggestion…*, 100 commits in a request: asking them of every commit would cost many more API points. A pull request is read again when it changed on GitHub since, and once more if it was read before all pages were read (``Item.THREADS``). Reading them needs a GitHub token, which the fetches of insight.pycal.org have; without one, the pages have no suggestions.

GitHub itself lists at most 250 commits of a pull request; a suggestion applied by a commit before those is found only if a reply names the commit.

.. _suggestion-badges:

Badges
======

A badge sums up the suggestions of a pull request, or of all pull requests of a person. The badge of a pull request is *suggestions | 3/5*: 3 of its 5 suggestions were applied. With ``?number=1`` at the end of its address it starts with the number of the pull request: *PR #12 suggestions | 3/5*; its page has a checkbox for that. The badge of a person is *ann | 3/5 suggestions applied*. The colours:

green
    All suggestions were applied.
red
    At least one suggestion is open.
yellow
    None is open, and at least one is unknown.
grey
    *no suggestions*: there are none, or they were not read yet.

The badge of a person is on the page of their badges, next to the badge of replies (``/s/<scope>/badges/<login>/``); the badge of a pull request is on its page of suggestions. :ref:`suggestion-badge-addresses` lists their addresses.

The pages
=========

**Suggestions** in the drop-down of a project shows the suggestions of all pull requests, and **Suggestions** in the drop-down of a person those on the pull requests of the person. Both group them by pull request: a line with the badge of the pull request opens the list of its suggestions. The newest suggestion comes first: the pull request with the newest suggestion is at the top, and within a pull request the suggestions are newest first.

Two rows of checkboxes choose what is shown:

**Suggestions:** unknown, open, applied
    The statuses of the suggestions; all are shown at first.
**Pull requests:** open, closed, merged
    The state of the pull requests; at first only the open ones, where a suggestion can still be applied. *Closed* is closed without a merge.

The badge of a pull request in the summary line counts all its suggestions, also those the checkboxes leave out. The page of one pull request shows its suggestions whatever its state.

The column **Suggestions addressed** of **Pull requests and issues** has the badge of each pull request with suggestions; it opens the suggestions of the pull request.
