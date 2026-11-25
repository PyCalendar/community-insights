"""A GitHub client that answers the queries of review threads in pages of a given size."""

from community_insights.sync.queries import (
    commit_authors_query,
    more_pull_commits_query,
    more_thread_comments_query,
    more_threads_query,
    threads_query,
)


def paged(nodes: list, after: str | None, size: int) -> dict:
    """A page of a connection: the nodes after the cursor, at most ``size``.

    Args:
        nodes: All nodes.
        after: The cursor: the index of the first node, as text; None for the first page.
        size: The nodes of a page.

    Returns:
        The page as GitHub answers it.
    """
    start = int(after or 0)
    end = start + size
    more = end < len(nodes)
    return {
        "pageInfo": {"hasNextPage": more, "endCursor": str(end) if more else None},
        "nodes": nodes[start:end],
    }


class PagedThreadsClient:
    """Pull requests with many threads, comments and commits, answered in small pages.

    The pull requests are given with all their threads (each with ``id`` and all comments) and
    commits (with ``id``, without authors); ``authors`` maps the id of a commit to the logins
    of its authors. Every query is recorded.
    """

    def __init__(self, pulls: list[dict], authors: dict[str, list[str]], size: int = 2):
        """The data and the size of the pages.

        Args:
            pulls: The pull requests: ``id``, ``threads`` and ``commits``.
            authors: The logins of the authors by the id of a commit.
            size: The nodes of a page.
        """
        self.pulls = {p["id"]: p for p in pulls}
        self.threads = {t["id"]: t for p in pulls for t in p["threads"]}
        self.authors = authors
        self.size = size
        self.queries: list[str] = []

    def thread(self, thread: dict) -> dict:
        """A thread with its first page of comments.

        Args:
            thread: The thread with all its comments.

        Returns:
            The thread as GitHub answers it.
        """
        return {
            "id": thread["id"],
            "isResolved": thread.get("isResolved", False),
            "resolvedBy": thread.get("resolvedBy"),
            "comments": paged(thread["comments"], None, self.size),
        }

    def threads_of(self, pull: dict, after: str | None) -> dict:
        """A page of the threads of a pull request.

        Args:
            pull: The pull request.
            after: The cursor.

        Returns:
            The page.
        """
        page = paged(pull["threads"], after, self.size)
        return {**page, "nodes": [self.thread(t) for t in page["nodes"]]}

    def commits_of(self, pull: dict, after: str | None) -> dict:
        """A page of the commits of a pull request, without their authors.

        Args:
            pull: The pull request.
            after: The cursor.

        Returns:
            The page.
        """
        return paged([{"commit": c} for c in pull["commits"]], after, self.size)

    async def graphql(self, query: str, **variables) -> dict:
        """Answer a query of the review threads like GitHub would.

        Args:
            query: The query.
            **variables: Its variables.

        Returns:
            The data.

        Raises:
            AssertionError: For another query.
        """
        self.queries.append(query)
        after = variables.get("after")
        if query == threads_query():
            return {
                "nodes": [
                    {
                        "id": p["id"],
                        "reviewThreads": self.threads_of(p, None),
                        "commits": self.commits_of(p, None),
                    }
                    if (p := self.pulls.get(i))
                    else None
                    for i in variables["ids"]
                ]
            }
        if query == more_threads_query():
            return {"node": {"reviewThreads": self.threads_of(self.pulls[variables["id"]], after)}}
        if query == more_thread_comments_query():
            comments = self.threads[variables["id"]]["comments"]
            return {"node": {"comments": paged(comments, after, self.size)}}
        if query == more_pull_commits_query():
            return {"node": {"commits": self.commits_of(self.pulls[variables["id"]], after)}}
        if query == commit_authors_query():
            assert len(variables["ids"]) <= 100
            return {
                "nodes": [
                    {
                        "id": i,
                        "authors": {"nodes": [{"user": {"login": a}} for a in self.authors[i]]},
                    }
                    for i in variables["ids"]
                ]
            }
        raise AssertionError(f"not a query of threads: {query}")
