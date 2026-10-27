import asyncio

from ...errors import GitHubRequestRejected
from ...models import Item, Repository


async def nothing() -> None:
    """The check that never stops anything.

    Returns:
        None.
    """
    return None


def number_at_end(url: str) -> int:
    """The number at the end of an address of an issue or pull request.

    Args:
        url: The address, such as ``https://api.github.com/repos/o/r/issues/12``.

    Returns:
        The number, such as 12.
    """
    return int(url.rstrip("/").rsplit("/", 1)[1])


def node(comment: dict, key: str) -> dict:
    """A comment of the REST API in the shape of a GraphQL node.

    Args:
        comment: The comment, as the REST API answers it.
        key: The name of its time: ``createdAt`` or ``submittedAt``.

    Returns:
        The node.
    """
    user = comment.get("user") or {}
    return {
        key: comment["created_at"],
        "author": {
            "login": user.get("login"),
            "__typename": "Bot" if user.get("type") == "Bot" else "User",
        }
        if user
        else None,
        "authorAssociation": comment.get("author_association", ""),
    }


class AnonymousSource:
    """Pull requests and issues from the REST API, without a token.

    Pull requests and issues without a token, from the REST API: all items, all issue comments
    and all review comments of the repository changed since the last fetch, about one request
    per 100 of them. Reviews without a comment, names and locations of people cannot be read
    like this. The events of an item are added to those read before, as only the new comments
    are read.
    """

    replaces_events = False

    def __init__(self, client):
        """Read repositories without a token, with the REST API of GitHub.

        Args:
            client: The client without a token (``AnonymousClient``).
        """
        self.client = client
        self.check = nothing
        # repository -> the load of both kinds: read once, also when both ask at once
        self.read: dict[str, asyncio.Future] = {}
        self.counted = 0

    @property
    def points(self) -> int:
        """Requests made and not yet counted, like TokenPool.points."""
        return self.client.requests - self.counted

    @points.setter
    def points(self, value: int) -> None:
        self.counted = self.client.requests - value

    async def close(self) -> None:
        """Close the connections."""
        await self.client.close()

    async def load(self, repository: Repository) -> dict[str, list]:
        """Both kinds at once, changed since the older of their last fetches.

        Args:
            repository: The repository.

        Returns:
            The pull requests and issues by kind.
        """
        full = repository.full_name
        if full not in self.read:
            self.read[full] = asyncio.ensure_future(self.read_both(repository))
        return await self.read[full]

    async def read_both(self, repository: Repository) -> dict[str, list]:
        """Read the items, comments and review comments changed since the last fetch.

        Args:
            repository: The repository.

        Returns:
            The pull requests and issues by kind, with their comments and reviews.
        """
        full = repository.full_name
        prs, issues = repository.prs_synced_until, repository.issues_synced_until
        since = min(prs, issues) if prs and issues else None
        changed = {"since": since.isoformat()} if since else {}
        order = {"sort": "updated", "direction": "desc"}
        await self.check()
        issues = await self.client.all_pages(
            f"/repos/{full}/issues", state="all", **order, **changed
        )
        await self.check()
        comments = await self.client.all_pages(f"/repos/{full}/issues/comments", **order, **changed)
        await self.check()
        reviews = await self.client.all_pages(f"/repos/{full}/pulls/comments", **order, **changed)
        by_issue: dict[int, list] = {}
        for comment in comments:
            by_issue.setdefault(number_at_end(comment["issue_url"]), []).append(
                node(comment, "createdAt")
            )
        by_pull: dict[int, list] = {}
        for comment in reviews:
            by_pull.setdefault(number_at_end(comment["pull_request_url"]), []).append(
                node(comment, "submittedAt")
            )
        found = {Item.PR: [], Item.ISSUE: []}
        for issue in issues:
            pull = issue.get("pull_request")
            user = issue.get("user") or {}
            item = {
                "id": issue["node_id"],
                "number": issue["number"],
                "title": issue["title"],
                "state": issue["state"].upper(),
                "createdAt": issue["created_at"],
                "updatedAt": issue["updated_at"],
                "closedAt": issue.get("closed_at"),
                "author": {
                    "login": user["login"],
                    "__typename": "Bot" if user.get("type") == "Bot" else "User",
                }
                if user
                else None,
                "authorAssociation": issue.get("author_association", ""),
                "comments": {
                    "nodes": by_issue.get(issue["number"], []),
                    "pageInfo": {"hasNextPage": False},
                },
            }
            if pull:
                item["merged"] = bool(pull.get("merged_at"))
                item["mergedBy"] = None
                item["reviews"] = {
                    "nodes": by_pull.get(issue["number"], []),
                    "pageInfo": {"hasNextPage": False},
                }
                found[Item.PR].append(item)
            else:
                found[Item.ISSUE].append(item)
        return found

    async def page(self, repository: Repository, kind: str, cursor, since) -> dict:
        """All items of a kind in one page.

        Args:
            repository: The repository.
            kind: ``pr`` or ``issue``.
            cursor: Not used: everything comes in one page.
            since: Not used: ``load`` decides what changed.

        Returns:
            The page, in the shape of the GraphQL answers.
        """
        found = await self.load(repository)
        return {"nodes": found[kind], "totalCount": None, "pageInfo": {"hasNextPage": False}}

    async def commits(self, repository: Repository, cursor, since) -> dict:
        """All commits since the last fetch, in one page (100 per request).

        Args:
            repository: The repository.
            cursor: Not used: everything comes in one page.
            since: The time of the last fetch, None for all commits.

        Returns:
            The commits, how many there are, and None for no next page.

        Raises:
            GitHubRequestRejected: If GitHub refuses the request, but not for an empty repository.
        """
        await self.check()
        changed = {"since": since.isoformat()} if since else {}
        try:
            found = await self.client.all_pages(f"/repos/{repository.full_name}/commits", **changed)
        except GitHubRequestRejected as error:
            if error.context.get("status") == 409:  # an empty repository
                return {"nodes": [], "total": 0, "next": None}
            raise
        nodes = [
            {
                "sha": c["sha"],
                "login": (c.get("author") or {}).get("login") or "",
                "name": ((c.get("commit") or {}).get("author") or {}).get("name") or "",
                "at": ((c.get("commit") or {}).get("committer") or {}).get("date"),
            }
            for c in found
        ]
        return {"nodes": [n for n in nodes if n["at"]], "total": None, "next": None}

    async def all_nodes(self, item: dict, field: str) -> list[dict]:
        """The comments or reviews of an item: all came with it.

        Args:
            item: The item, with its comments or reviews.
            field: ``comments`` or ``reviews``.

        Returns:
            The comments or reviews.
        """
        return list(item[field]["nodes"])

    async def people(self, logins: list[str]) -> dict:
        """Nobody's name or location: they need a token.

        Args:
            logins: The logins.

        Returns:
            None for each login.
        """
        return dict.fromkeys(logins)  # names and locations need a token
