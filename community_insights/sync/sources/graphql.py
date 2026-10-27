from ...models import Repository
from ..queries import FIELDS, INNER, MORE, PAGE, commits_query, list_query, more_query


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

    async def people(self, logins: list[str]) -> dict:
        """Name, location and avatar of a batch of people.

        Args:
            logins: The logins.

        Returns:
            The profile of each login, None for those GitHub does not know.
        """
        await self.check()
        return await self.client.people(logins)
