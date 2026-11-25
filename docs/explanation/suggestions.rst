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
    #. **Resolved by somebody else.** The author or a third person resolved the thread without a commit named in it. The suggestion may have been applied, or turned down.
    #. **Answered with another suggestion.** A later comment in the thread suggests other code. The new suggestion counts on its own.
open
    Anything else: the suggestion is not applied yet.

The pages also show why a suggestion has its status, such as *a reply names a commit*.

**Last in the thread** names who of the author of the pull request and the suggester wrote last in the thread of the suggestion, and links to that message. Others who wrote in the thread do not count: the question is whose turn it is.

How the suggestions are read
============================

The suggestions are read from GitHub with the fetch of a repository: the review threads of each pull request that got a review, the comments of each thread, and the last commits of the pull request. A pull request is read again when it changed on GitHub since. Reading them needs a GitHub token; without one, the pages have no suggestions.

Limits: the first 50 review threads of a pull request, the first 20 comments of each thread and the last 100 commits are read. A suggestion in a longer thread, or applied by an older commit, can be missed.

.. _suggestion-badges:

Badges
======

A badge sums up the suggestions of a pull request, or of all pull requests of a person, such as *PR #12 | 3/5 suggestions applied* or *ann | 3/5 suggestions applied*:

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

**Suggestions** in the drop-down of a project shows the suggestions of all pull requests, and **Suggestions** in the drop-down of a person those on the pull requests of the person. Both group them by pull request: a line with the badge of the pull request opens the list of its suggestions. The pull requests with an unknown suggestion come first, then those with an open one, then those where all were applied, and then by their number. Within a pull request, the suggestions are in the same order. **Show** switches the statuses on and off.

The column **Suggestions addressed** of **Pull requests and issues** has the badge of each pull request with suggestions; it opens the suggestions of the pull request.
