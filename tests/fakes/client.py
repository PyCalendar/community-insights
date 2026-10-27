"""A GitHub client that answers the GraphQL queries of community_insights/github and
community_insights/sync from prepared data, like GitHub would."""

import re

from community_insights.github import RateLimit, reads

from .builders import connection


class FakeClient:
    """A GitHub client that answers the queries of the sync from prepared data."""

    token = "token"

    def __init__(
        self, prs=(), issues=(), people=None, repositories=(), suggested=(), hidden=(), commits=()
    ):
        """The data to answer with; hidden repositories are not visible to the token."""
        self.prs, self.issues = list(prs), list(issues)
        self.commits = list(commits)  # {"oid", "committedDate", "author": {"name", "user"}}
        self.known = people or {}
        self.listed = list(repositories)
        self.suggested = list(suggested)
        self.hidden = set(hidden)  # repositories this token cannot see
        self.more: dict = {}  # (item id, "comments" or "reviews") -> further nodes
        self.requests = 0
        self.rate = RateLimit()

    async def graphql(self, query, **variables):
        """Answer a query like GitHub would, counting the requests."""
        self.requests += 1
        if "history(first: 100" in query:
            since = variables.get("since") or ""
            nodes = sorted(
                (c for c in self.commits if c["committedDate"] > since),
                key=lambda c: c["committedDate"],
                reverse=True,
            )
            history = {
                "totalCount": len(self.commits),
                "pageInfo": {"hasNextPage": False, "endCursor": None},
                "nodes": nodes,
            }
            return {"repository": {"defaultBranchRef": {"target": {"history": history}}}}
        if "node(id: $id)" in query:
            field = "comments" if "comments(" in query else "reviews"
            return {"node": {field: connection(*self.more.get((variables["id"], field), []))}}
        if "organizations(first" in query:
            return {"viewer": self.suggestions_answer()}
        if query.strip() == "query { viewer { login } }":
            return {"viewer": {"login": "alice"}}
        if "repositories(first: 100" in query:
            page = {"nodes": self.listed, "pageInfo": {"hasNextPage": False, "endCursor": None}}
            root = "viewer" if "repositoryOwner" not in query else "repositoryOwner"
            return {root: {"repositories": page}}
        if (
            "repository(owner: $owner, name: $name) {" in query
            and "pullRequests(" not in query
            and "issues(" not in query
        ):
            name = f"{variables['owner']}/{variables['name']}"
            found = next((r for r in self.listed if r["nameWithOwner"] == name), None)
            return {"repository": found}
        if re.search(r"\br0: repository", query):
            return self.each_repository(query)
        if re.search(r"\bu0: user", query):
            return {
                f"u{i}": self.known.get(variables[f"l{i}"])
                for i in range(len([k for k in variables if k.startswith("l")]))
            }
        field = "pullRequests" if "pullRequests(" in query else "issues"
        items = self.prs if field == "pullRequests" else self.issues
        items = sorted(items, key=lambda i: i["updatedAt"], reverse=True)
        return {"repository": {field: {**connection(*items), "totalCount": len(items)}}}

    def each_repository(self, query: str) -> dict:
        """The answer to a query of several repositories."""
        names = re.findall(r'r(\d+): repository\(owner: "([^"]*)", name: "([^"]*)"\)', query)
        answer = {}
        for index, owner, name in names:
            full = f"{owner}/{name}"
            if full in self.hidden:
                answer[f"r{index}"] = None
            elif "totalCount" in query:
                answer[f"r{index}"] = {
                    "pullRequests": {"totalCount": len(self.prs)},
                    "issues": {"totalCount": len(self.issues)},
                }
            else:
                answer[f"r{index}"] = {"id": full}
        return answer

    def suggestions_answer(self) -> dict:
        """The answer to the query of the suggestions."""
        nodes = [
            {"nameWithOwner": s["name"], "stargazerCount": s.get("stars", 0)}
            for s in self.suggested
        ]
        empty = {"nodes": []}
        return {
            "organizations": empty,
            "repositories": {"nodes": nodes},
            "repositoriesContributedTo": empty,
        }

    # the reads, like the real client: through graphql
    async def viewer(self):
        """The owner of the token."""
        return await reads.viewer(self.graphql)

    async def repositories(self, owner=None, limit=300):
        """The repositories of an owner."""
        return await reads.repositories(self.graphql, owner, limit)

    async def repository(self, full_name):
        """One repository."""
        return await reads.repository(self.graphql, full_name)

    async def suggestions(self):
        """The repositories and organisations to offer."""
        return await reads.suggestions(self.graphql)

    async def visible(self, full_names):
        """Whether the token sees each repository."""
        return await reads.visible(self.graphql, full_names)

    async def totals(self, full_names):
        """The pull requests and issues of each repository."""
        return await reads.totals(self.graphql, full_names)

    async def people(self, logins):
        """The profiles of people."""
        return await reads.people(self.graphql, logins)

    async def close(self):
        """Nothing to close."""
        pass
