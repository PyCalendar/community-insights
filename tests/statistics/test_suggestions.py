"""Code suggestions: what one is, and when it is applied, open or unknown."""

import pytest

from community_insights.stats.suggestion_summary import SuggestionSummary
from community_insights.sync.suggestions import (
    APPLIED,
    OPEN,
    UNKNOWN,
    is_suggestion,
    names_commit,
    suggestions_of,
)

SUGGESTED = "Better so?\n```suggestion\nx = 1\n```"


def comment(login, minute, body=SUGGESTED, outdated=False, number=None):
    """A review comment as GitHub answers it.

    Args:
        login: Who wrote it.
        minute: When, in minutes after 10:00 on 5 January 2026.
        body: Its text.
        outdated: Whether its lines changed since.
        number: Its id; by the minute.

    Returns:
        The comment.
    """
    return {
        "databaseId": number or minute,
        "body": body,
        "url": f"https://github.com/o/r/pull/1#discussion_r{number or minute}",
        "createdAt": f"2026-01-05T10:{minute:02d}:00Z",
        "outdated": outdated,
        "path": "a.py",
        "author": {"login": login},
    }


def thread(*comments, resolved_by=None):
    """A review thread.

    Args:
        *comments: Its comments.
        resolved_by: Who resolved it; None if it is not resolved.

    Returns:
        The thread.
    """
    return {
        "isResolved": resolved_by is not None,
        "resolvedBy": {"login": resolved_by} if resolved_by else None,
        "comments": {"nodes": list(comments)},
    }


def pull(*threads, commits=()):
    """A pull request with review threads and commits.

    Args:
        *threads: Its threads.
        commits: (minute, headline, logins of the authors) of its commits.

    Returns:
        The pull request.
    """
    return {
        "id": "pr1",
        "reviewThreads": {"nodes": list(threads)},
        "commits": {
            "nodes": [
                {
                    "commit": {
                        "committedDate": f"2026-01-05T10:{minute:02d}:00Z",
                        "messageHeadline": headline,
                        "authors": {"nodes": [{"user": {"login": a}} for a in authors]},
                    }
                }
                for minute, headline, authors in commits
            ]
        },
    }


def status(data, author="ann"):
    """The statuses and reasons of the suggestions of a pull request.

    Args:
        data: The pull request.
        author: Its author.

    Returns:
        (status, reason) of each suggestion.
    """
    return [(s["status"], s["reason"]) for s in suggestions_of(data, author)]


def test_a_suggestion_has_suggested_code():
    """A block of suggested code, not any code, not plain text."""
    assert is_suggestion(SUGGESTED)
    assert is_suggestion("  ````suggestion\ny\n````")
    assert not is_suggestion("```python\nx = 1\n```")
    assert not is_suggestion("I suggest to rename it.")
    data = pull(thread(comment("bob", 1, "Rename it?"), comment("ann", 2, "ok")))
    assert suggestions_of(data, "ann") == [], "comments without suggested code are no suggestions"


@pytest.mark.parametrize(
    ("body", "named"),
    [
        ("Done in 3f2c9ab.", True),
        ("Fixed: https://github.com/o/r/commit/3f2c9ab1d", True),
        ("see https://github.com/o/r/pull/1/commits/abc1234def", True),
        ("Thanks, done!", False),
        ("issue 1234567", False),
        ("deadbeef is a word", False),
        ("```suggestion\nabc1234f\n```", False),
    ],
)
def test_a_reply_that_names_a_commit(body, named):
    """A hash with digits and letters, or the address of a commit; not in suggested code."""
    assert names_commit(body) is named


def test_committed_from_github():
    """Commit suggestion: a later commit "Apply suggestion" with the suggester, lines changed."""
    data = pull(
        thread(comment("bob", 1, outdated=True)),
        commits=[(5, "Apply suggestions from code review", ["ann", "bob"])],
    )
    assert status(data) == [(APPLIED, "commit-suggestion")]


@pytest.mark.parametrize(
    ("outdated", "commit"),
    [
        (False, (5, "Apply suggestions from code review", ["ann", "bob"])),  # lines unchanged
        (True, (0, "Apply suggestions from code review", ["ann", "bob"])),  # before it
        (True, (5, "Apply suggestions from code review", ["ann", "cid"])),  # of another
        (True, (5, "Fix the tests", ["ann", "bob"])),  # no commit of GitHub
    ],
)
def test_not_committed_from_github(outdated, commit):
    """Each of the conditions is needed."""
    data = pull(thread(comment("bob", 1, outdated=outdated)), commits=[commit])
    assert status(data) == [(OPEN, "")]


def test_a_reply_names_a_commit():
    """The author answers with the commit that applies it."""
    data = pull(thread(comment("bob", 1), comment("ann", 3, "Done in 3f2c9ab.")))
    assert status(data) == [(APPLIED, "commit-named")]


def test_resolved_by_the_suggester():
    """The suggester resolved the thread: applied."""
    assert status(pull(thread(comment("bob", 1), resolved_by="bob"))) == [
        (APPLIED, "resolved-by-suggester")
    ]


def test_resolved_by_somebody_else():
    """The author or a third person resolved it: unknown."""
    assert status(pull(thread(comment("bob", 1), resolved_by="ann"))) == [
        (UNKNOWN, "resolved-by-other")
    ]


def test_answered_with_another_suggestion():
    """The answer is a suggestion, too: the first is unknown, the answer is open."""
    data = pull(thread(comment("bob", 1), comment("ann", 2, SUGGESTED)))
    assert status(data) == [(UNKNOWN, "answered-with-suggestion"), (OPEN, "")]


def test_open():
    """Nothing happened: open."""
    assert status(pull(thread(comment("bob", 1), comment("ann", 2, "Why?")))) == [(OPEN, "")]


def test_who_wrote_last_in_the_thread():
    """Of the author and the suggester, who wrote last; a third person does not count."""
    data = pull(thread(comment("bob", 1), comment("ann", 2, "Why?"), comment("cid", 3, "+1")))
    found = suggestions_of(data, "ann")[0]
    assert (found["last_by"], found["last_role"]) == ("ann", "author")
    assert found["last_url"].endswith("discussion_r2")
    data = pull(thread(comment("bob", 1)))
    found = suggestions_of(data, "ann")[0]
    assert (found["last_by"], found["last_role"]) == ("bob", "suggester")


def test_a_suggestion_on_the_own_pull_request():
    """The author suggests to themself: the author wrote last."""
    found = suggestions_of(pull(thread(comment("Ann", 1))), "ann")[0]
    assert found["last_role"] == "author"


def test_a_deleted_account_and_empty_answers():
    """No author, no threads, no commits: nothing breaks."""
    data = {"id": "x", "reviewThreads": None, "commits": None}
    assert suggestions_of(data, "ann") == []
    ghost = comment("bob", 1)
    ghost["author"] = None
    assert status(pull(thread(ghost))) == [(OPEN, "")]


@pytest.mark.parametrize(
    ("counts", "colour", "message"),
    [
        ((3, 0, 0), "green", "3/3 suggestions applied"),
        ((2, 1, 0), "red", "2/3 suggestions applied"),
        ((2, 1, 1), "red", "2/4 suggestions applied"),
        ((2, 0, 1), "yellow", "2/3 suggestions applied"),
        ((0, 0, 1), "yellow", "0/1 suggestions applied"),
        ((0, 0, 0), "grey", "no suggestions"),
    ],
)
def test_the_colours_of_the_badges(counts, colour, message):
    """Green: all applied; red: one open; yellow: applied or unknown; grey: none."""
    summary = SuggestionSummary(*counts)
    assert (summary.status, summary.message) == (colour, message)
