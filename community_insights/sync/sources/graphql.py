from ...models import Repository
from ..queries import (
    APPLY_COMMITS,
    FIELDS,
    INNER,
    MORE,
    PAGE,
    commit_authors_query,
    commits_query,
    details_query,
    list_query,
    more_pull_commits_query,
    more_query,
    more_thread_comments_query,
    more_threads_query,
    threads_query,
)
from ..suggestions import applying_commits


async def nothing() -> None:
    """The check that never stops anything.

    Returns:
        None.
    """
    return None


class GraphQLSource:
    """Pull requests and issues from GraphQL, with a client or a token pool.

    Pages of pull requests or issues with their first comments and reviews, from a Client or a
    TokenPool; the rest of the comments of an item when it has more. Every request is preceded
    by `check()`.
    """

    replaces_events = True  # an item comes with all its comments and reviews
    reads_details = True  # the commits and closers of pull requests read before
    reads_threads = True  # the review threads with the suggestions

    def __init__(self, client):
        """Read repositories with GraphQL and tokens.

        Args:
            client: The client or the pool of tokens.
        """
        self.client = client
        self.check = nothing

    async def query(self, query: str, **variables) -> dict:
        """Send a query after the check.

        Args:
            query: The GraphQL query.
            **variables: Its variables.

        Returns:
            The data of the answer.
        """
        await self.check()
        return await self.client.graphql(query, **variables)

    async def page(self, repository: Repository, kind: str, cursor, since) -> dict:
        """A page of pull requests or issues, newest change first.

        Args:
            repository: The repository.
            kind: ``pr`` or ``issue``.
            cursor: The cursor of the page, None for the first one.
            since: Not used: the syncer stops at the last change read.

        Returns:
            The page as GitHub answers it: nodes, total and the page info.
        """
        owner, name = repository.full_name.split("/", 1)
        answer = await self.query(
            list_query(kind), owner=owner, name=name, after=cursor, page=PAGE, inner=INNER
        )
        return answer["repository"][FIELDS[kind]]

    async def commits(self, repository: Repository, cursor, since) -> dict:
        """A page of commits of the default branch.

        A page of commits: {"nodes": [{"sha", "login", "name", "at"}], "total", "next"} with
        "next" the cursor of the next page or None.

        Args:
            repository: The repository.
            cursor: The cursor of the page, None for the first one.
            since: The time of the last fetch, None for all commits.

        Returns:
            The page.
        """
        owner, name = repository.full_name.split("/", 1)
        answer = await self.query(
            commits_query(),
            owner=owner,
            name=name,
            after=cursor,
            since=since.isoformat() if since else None,
        )
        branch = (answer.get("repository") or {}).get("defaultBranchRef")
        if not branch or not branch.get("target"):
            return {"nodes": [], "total": 0, "next": None}  # an empty repository
        history = branch["target"]["history"]
        nodes = [
            {
                "sha": n["oid"],
                "login": ((n.get("author") or {}).get("user") or {}).get("login") or "",
                "name": (n.get("author") or {}).get("name") or "",
                "at": n["committedDate"],
            }
            for n in history["nodes"]
        ]
        info = history["pageInfo"]
        return {
            "nodes": nodes,
            "total": history["totalCount"],
            "next": info["endCursor"] if info["hasNextPage"] else None,
        }

    async def all_nodes(self, item: dict, field: str) -> list[dict]:
        """The comments or reviews of an item, with the pages after the first.

        Args:
            item: The item as GitHub answered it.
            field: ``comments`` or ``reviews``.

        Returns:
            All comments or reviews.
        """
        found = item[field]
        nodes = list(found["nodes"])
        while found["pageInfo"]["hasNextPage"]:
            answer = await self.query(
                more_query(field), id=item["id"], after=found["pageInfo"]["endCursor"], inner=MORE
            )
            found = answer["node"][field]
            nodes += found["nodes"]
        return nodes

    async def details(self, ids: list[str]) -> list[dict | None]:
        """The last commits and the closer of pull requests.

        Args:
            ids: The node ids of the pull requests, at most ``queries.DETAILS``.

        Returns:
            The pull requests as GitHub answers them; None for one it no longer has.
        """
        answer = await self.query(details_query(), ids=ids)
        return answer["nodes"]

    async def threads(self, ids: list[str]) -> list[dict | None]:
        """All review threads, their comments and the commits of pull requests.

        What does not fit into the first request is read in further pages: every thread,
        every comment of a thread and every commit. The authors are added to the commits that
        applied suggestions.

        Args:
            ids: The node ids of the pull requests, at most ``queries.THREADS``.

        Returns:
            The pull requests as GitHub answers them, with all pages; None for one it no
            longer has.
        """
        answer = await self.query(threads_query(), ids=ids)
        pulls = answer["nodes"]
        for pull in pulls:
            if pull:
                await self.rest_of_threads(pull)
        await self.commit_authors(applying_commits(pulls))
        return pulls

    async def rest_of(self, found: dict | None, query: str, node_id: str, field: str) -> dict:
        """A connection with all its pages: the nodes of the first and the following ones.

        Args:
            found: The connection as GitHub answered it first, with ``pageInfo``.
            query: The query of the next page, with ``id`` and ``after``.
            node_id: The id of the node the connection belongs to.
            field: The name of the connection, such as ``reviewThreads``.

        Returns:
            The connection with all nodes and no next page.
        """
        found = found or {}
        nodes = list(found.get("nodes") or [])
        info = found.get("pageInfo") or {}
        while info.get("hasNextPage"):
            answer = await self.query(query, id=node_id, after=info["endCursor"])
            page = (answer.get("node") or {}).get(field) or {}
            nodes += page.get("nodes") or []
            info = page.get("pageInfo") or {}
        return {"nodes": nodes, "pageInfo": {"hasNextPage": False, "endCursor": None}}

    async def rest_of_threads(self, pull: dict) -> None:
        """Read the further threads, comments of threads and commits of a pull request.

        Args:
            pull: The pull request as GitHub answered it first; it gets all pages.
        """
        pull["reviewThreads"] = await self.rest_of(
            pull.get("reviewThreads"), more_threads_query(), pull["id"], "reviewThreads"
        )
        for thread in pull["reviewThreads"]["nodes"]:
            if thread and thread.get("id"):
                thread["comments"] = await self.rest_of(
                    thread.get("comments"), more_thread_comments_query(), thread["id"], "comments"
                )
        pull["commits"] = await self.rest_of(
            pull.get("commits"), more_pull_commits_query(), pull["id"], "commits"
        )

    async def commit_authors(self, commits: list[dict]) -> None:
        """Add the authors and co-authors to commits, in requests of ``APPLY_COMMITS``.

        Args:
            commits: The commits as GitHub answered them, with ``id``; each gets ``authors``.
        """
        for start in range(0, len(commits), APPLY_COMMITS):
            part = commits[start : start + APPLY_COMMITS]
            answer = await self.query(commit_authors_query(), ids=[c["id"] for c in part])
            authors = {n["id"]: n.get("authors") for n in answer.get("nodes") or [] if n}
            for commit in part:
                commit["authors"] = (
                    authors.get(commit["id"]) or commit.get("authors") or {"nodes": []}
                )

    async def people(self, logins: list[str]) -> dict:
        """Name, location and avatar of a batch of people.

        Args:
            logins: The logins.

        Returns:
            The profile of each login, None for those GitHub does not know.
        """
        await self.check()
        return await self.client.people(logins)
