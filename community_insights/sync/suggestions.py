"""The code suggestions of a pull request and whether they were applied, from its review threads.

A suggestion is a review comment with a block of suggested code (```` ```suggestion ````).
Its status:

applied
    GitHub's **Commit suggestion** or **Add suggestion to batch** applied it: a later commit
    of the pull request is named "Apply suggestion(s) ..." and has the suggester as an author
    or co-author, and the lines of the suggestion changed since (GitHub marks the comment
    outdated). Or a later comment of the thread names a commit (its hash or address). Or the
    suggester resolved the thread.
unknown
    The thread was resolved by somebody else than the suggester, or the suggestion was
    answered with another suggestion.
open
    Anything else: the suggestion is not applied yet.
"""

import re
from datetime import datetime

from django.utils.dateparse import parse_datetime

APPLIED, OPEN, UNKNOWN = "applied", "open", "unknown"
STATUSES = (UNKNOWN, OPEN, APPLIED)  # the order of the pages: what needs a look first
SUGGESTION = re.compile(r"^\s*```+\s*suggestion\b", re.MULTILINE)
# the commits GitHub makes for "Commit suggestion" and "Add suggestion to batch"
APPLY = re.compile(r"^apply (suggestions? from|suggestions? from code review)", re.IGNORECASE)
# a commit named in a comment: its hash (7 to 40 hexadecimal digits with a digit and a
# letter, not a plain number or word) or its address
COMMIT_URL = re.compile(r"/commit/[0-9a-f]{7,40}\b|/pull/\d+/commits/[0-9a-f]{7,40}\b", re.I)
HASH = re.compile(r"(?<![\w/])(?=[0-9a-f]*[a-f])(?=[0-9a-f]*\d)[0-9a-f]{7,40}(?![\w])")


def is_suggestion(body: str) -> bool:
    r"""Whether a comment suggests code: it has a block ```` ```suggestion ````.

    Args:
        body: The text of the comment, in Markdown.

    Returns:
        True for a suggestion.

    Examples:
        >>> is_suggestion("Better:\n```suggestion\nx = 1\n```"), is_suggestion("```python")
        (True, False)
    """
    return bool(SUGGESTION.search(body or ""))


def names_commit(body: str) -> bool:
    """Whether a comment names a commit: by its address or its hash.

    Args:
        body: The text of the comment.

    Returns:
        True if it names one.

    Examples:
        >>> names_commit("Done in 3f2c9ab."), names_commit("https://github.com/o/r/commit/3f2c9ab1")
        (True, True)
        >>> names_commit("Thanks, done!"), names_commit("issue 1234567")
        (False, False)
    """
    text = SUGGESTION.split(body or "")[0]  # not the code of a suggestion
    return bool(COMMIT_URL.search(text) or HASH.search(text))


def login_of(node: dict | None) -> str:
    """The login of the author of a node, "" for a deleted account.

    Args:
        node: A node with ``author`` or a user.

    Returns:
        The login.
    """
    return ((node or {}).get("author") or {}).get("login") or ""


def apply_commits(data: dict) -> list[tuple[datetime | None, set[str]]]:
    """The commits that applied suggestions: when, and the logins of their authors.

    Args:
        data: The pull request as GitHub answered the query of threads.

    Returns:
        The time and the authors (lowercase) of each commit named "Apply suggestion...".
    """
    found = []
    for node in ((data.get("commits") or {}).get("nodes")) or []:
        commit = (node or {}).get("commit") or {}
        if not APPLY.search(commit.get("messageHeadline") or ""):
            continue
        authors = {
            ((a or {}).get("user") or {}).get("login", "").lower()
            for a in ((commit.get("authors") or {}).get("nodes") or [])
        }
        found.append((parse_datetime(commit["committedDate"]), authors - {""}))
    return found


def status_of(
    comment: dict,
    later: list[dict],
    thread: dict,
    applies: list[tuple[datetime | None, set[str]]],
) -> tuple[str, str]:
    """The status of a suggestion and why.

    Args:
        comment: The comment with the suggestion.
        later: The comments after it in its thread.
        thread: The thread: ``isResolved`` and ``resolvedBy``.
        applies: The commits that applied suggestions (``apply_commits``).

    Returns:
        The status (``applied``, ``unknown`` or ``open``) and the reason: ``commit-suggestion``,
        ``commit-named``, ``resolved-by-suggester``, ``resolved-by-other``,
        ``answered-with-suggestion`` or "" for an open one.
    """
    suggester = login_of(comment).lower()
    at = parse_datetime(comment["createdAt"])
    if (
        at is not None
        and comment.get("outdated")
        and any(when and when > at and suggester in authors for when, authors in applies)
    ):
        return APPLIED, "commit-suggestion"
    if any(names_commit(c.get("body") or "") for c in later):
        return APPLIED, "commit-named"
    resolver = ((thread.get("resolvedBy") or {}).get("login") or "").lower()
    if thread.get("isResolved") and resolver and resolver == suggester:
        return APPLIED, "resolved-by-suggester"
    if thread.get("isResolved"):
        return UNKNOWN, "resolved-by-other"
    if any(is_suggestion(c.get("body") or "") for c in later):
        return UNKNOWN, "answered-with-suggestion"
    return OPEN, ""


def suggestions_of(data: dict, pr_author: str) -> list[dict]:
    """The suggestions of a pull request with their status and who wrote last in the thread.

    Args:
        data: The pull request as GitHub answered the query of threads.
        pr_author: The login of the author of the pull request.

    Returns:
        For each suggestion: ``comment_id``, ``url``, ``author``, ``created_at``, ``path``,
        ``status``, ``reason``, ``resolved``, ``resolved_by``, and of the author of the pull
        request and the suggester, who wrote last in the thread: ``last_by``, ``last_role``
        (``author`` or ``suggester``), ``last_at`` and ``last_url``.
    """
    applies = apply_commits(data)
    found = []
    for thread in ((data.get("reviewThreads") or {}).get("nodes")) or []:
        comments = [c for c in ((thread.get("comments") or {}).get("nodes") or []) if c]
        for index, comment in enumerate(comments):
            if not is_suggestion(comment.get("body") or ""):
                continue
            later = comments[index + 1 :]
            status, reason = status_of(comment, later, thread, applies)
            suggester = login_of(comment)
            people = {pr_author.lower(): "author", suggester.lower(): "suggester"}
            if pr_author.lower() == suggester.lower():
                people = {pr_author.lower(): "author"}
            last = None
            for written in [comment, *later]:
                if login_of(written).lower() in people:
                    last = written
            found.append(
                {
                    "comment_id": comment.get("databaseId") or 0,
                    "url": comment.get("url") or "",
                    "author": suggester,
                    "created_at": parse_datetime(comment["createdAt"]),
                    "path": comment.get("path") or "",
                    "status": status,
                    "reason": reason,
                    "resolved": bool(thread.get("isResolved")),
                    "resolved_by": ((thread.get("resolvedBy") or {}).get("login") or ""),
                    "last_by": login_of(last),
                    "last_role": people.get(login_of(last).lower(), "") if last else "",
                    "last_at": parse_datetime(last["createdAt"]) if last else None,
                    "last_url": (last or {}).get("url") or "",
                }
            )
    return found
