"""All review threads, comments and commits are read, also beyond the first page."""

import pytest
from asgiref.sync import async_to_sync

from community_insights.sync.queries import (
    commit_authors_query,
    more_pull_commits_query,
    more_thread_comments_query,
    more_threads_query,
)
from community_insights.sync.sources.graphql import GraphQLSource
from community_insights.sync.suggestions import suggestions_of
from tests.fakes.paged_threads import PagedThreadsClient

SUGGESTED = "```suggestion\nx = 1\n```"


def comment(number: int, login: str, minute: int, body: str = SUGGESTED, outdated=False):
    """A review comment.

    Args:
        number: Its id.
        login: Who wrote it.
        minute: When, in minutes after 10:00 on 5 January 2026.
        body: The text.
        outdated: Whether its lines changed.

    Returns:
        The comment.
    """
    return {
        "databaseId": number,
        "body": body,
        "url": f"https://github.com/o/r/pull/1#discussion_r{number}",
        "createdAt": f"2026-01-05T10:{minute:02d}:00Z",
        "outdated": outdated,
        "path": "a.py",
        "author": {"login": login},
    }


def commit(number: int, minute: int, headline: str = "Fix") -> dict:
    """A commit of the pull request.

    Args:
        number: Makes its id.
        minute: When.
        headline: The first line of its message.

    Returns:
        The commit, without authors.
    """
    return {
        "id": f"c{number}",
        "committedDate": f"2026-01-05T10:{minute:02d}:00Z",
        "messageHeadline": headline,
    }


def pull_with_pages() -> dict:
    """A pull request with 5 threads of 5 comments and 5 commits: 3 pages of 2 each.

    The suggestion of the last thread is answered by a commit in its last comment; that of
    the fourth thread is applied by the last commit, by GitHub.

    Returns:
        The pull request.
    """
    threads = []
    for t in range(5):
        talk = [
            comment(t * 10 + c, "ann" if c % 2 else "bob", t * 10 + c, "ok") for c in range(1, 5)
        ]
        first = comment(t * 10, "bob", t * 10, outdated=t == 3)
        threads.append({"id": f"t{t}", "comments": [first, *talk]})
    threads[4]["comments"][-1]["body"] = "Done in 3f2c9ab."
    commits = [commit(n, n) for n in range(4)] + [
        commit(4, 59, "Apply suggestions from code review")
    ]
    return {"id": "pr1", "threads": threads, "commits": commits}


def read(client) -> list[dict | None]:
    """The pull requests as the source reads them.

    Args:
        client: The client.

    Returns:
        The pull requests.
    """
    return async_to_sync(GraphQLSource(client).threads)(["pr1", "gone"])


def test_every_thread_comment_and_commit_is_read():
    """Beyond the first page: 5 threads, 5 comments each and 5 commits."""
    client = PagedThreadsClient([pull_with_pages()], {"c4": ["bob", "ann"]})
    pull, gone = read(client)
    assert gone is None
    assert [t["id"] for t in pull["reviewThreads"]["nodes"]] == ["t0", "t1", "t2", "t3", "t4"]
    assert all(len(t["comments"]["nodes"]) == 5 for t in pull["reviewThreads"]["nodes"])
    assert [n["commit"]["id"] for n in pull["commits"]["nodes"]] == ["c0", "c1", "c2", "c3", "c4"]
    assert client.queries.count(more_threads_query()) == 2
    assert client.queries.count(more_thread_comments_query()) == 5 * 2
    assert client.queries.count(more_pull_commits_query()) == 2


def test_only_the_commits_that_applied_suggestions_get_their_authors():
    """The authors are asked of the commits named "Apply suggestion...", in one request."""
    client = PagedThreadsClient([pull_with_pages()], {"c4": ["bob", "ann"]})
    pull, _ = read(client)
    assert client.queries.count(commit_authors_query()) == 1
    commits = {n["commit"]["id"]: n["commit"] for n in pull["commits"]["nodes"]}
    assert [a["user"]["login"] for a in commits["c4"]["authors"]["nodes"]] == ["bob", "ann"]
    assert "authors" not in commits["c0"]


def test_the_later_pages_decide_the_status():
    """The commit named in the last comment and the commit on the last page count."""
    client = PagedThreadsClient([pull_with_pages()], {"c4": ["bob"]})
    pull, _ = read(client)
    found = {s["comment_id"]: (s["status"], s["reason"]) for s in suggestions_of(pull, "ann")}
    assert found == {
        0: ("open", ""),
        10: ("open", ""),
        20: ("open", ""),
        30: ("applied", "commit-suggestion"),
        40: ("applied", "commit-named"),
    }


def test_no_commit_applied_a_suggestion():
    """Without such a commit, no authors are asked."""
    data = pull_with_pages()
    data["commits"] = data["commits"][:2]
    client = PagedThreadsClient([data], {})
    read(client)
    assert commit_authors_query() not in client.queries


def test_many_commits_that_applied_suggestions():
    """The authors of more than 100 commits are asked in requests of 100."""
    data = pull_with_pages()
    data["commits"] = [commit(n, 59, "Apply suggestion from @bob") for n in range(150)]
    client = PagedThreadsClient([data], {f"c{n}": ["bob"] for n in range(150)}, size=100)
    read(client)
    assert client.queries.count(commit_authors_query()) == 2


@pytest.mark.django_db
def test_pull_requests_read_with_the_first_pages_only_are_read_again(user):
    """Read before all pages were read (version 0): the next fetch reads them again."""
    from community_insights.models import Item
    from community_insights.sync import store
    from tests.pages.test_suggestions import suggestion_client

    from ..data import read_repository
    from ..fakes import repo

    repository = store.store_repository(repo("o/r", 5))
    read_repository(suggestion_client(), repository)
    assert store.without_threads(repository) == []
    assert set(Item.objects.filter(number=1).values_list("threads_version", flat=True)) == {1}
    Item.objects.update(threads_version=0)
    assert len(store.without_threads(repository)) == 5, "the reviewed pull requests"
