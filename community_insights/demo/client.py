import random
from datetime import UTC, datetime, timedelta

from ..github import RateLimit

PEOPLE = [
    ("ada", "MEMBER", "London"),
    ("grace", "OWNER", "New York"),
    ("linus", "COLLABORATOR", "Portland"),
    ("margaret", "CONTRIBUTOR", "Boston"),
    ("tim", "CONTRIBUTOR", "Geneva"),
    ("barbara", "NONE", "Berlin"),
    ("ken", "FIRST_TIME_CONTRIBUTOR", "Tokyo"),
    ("radia", "NONE", "Sydney"),
]
BOTS = ["dependabot", "pre-commit-ci"]
START = datetime(2025, 1, 6, tzinfo=UTC)


class DemoClient:
    """Answers the queries of the sync with made up data.

    Answers the queries of the sync like GitHub would, with made up pull requests, issues,
    comments and reviews. The same seed gives the same data.
    """

    def __init__(self, seed: int = 1, prs: int = 80, issues: int = 60):
        self.random = random.Random(seed)
        self.items = {
            "pullRequests": self.make(prs, pr=True),
            "issues": self.make(issues, pr=False),
        }
        self.commits = self.make_commits(prs * 3)
        self.requests = 0
        self.rate = RateLimit()

    def when(self, after: datetime, hours: float) -> datetime:
        """A random time after another one, about `hours` later on average."""
        return after + timedelta(hours=self.random.expovariate(1 / hours))

    def node(self, login, association, at, typename="User", key="createdAt"):
        """A comment or review as GitHub answers it."""
        return {
            key: at.isoformat(),
            "author": {"login": login, "__typename": typename},
            "authorAssociation": association,
        }

    def responses(self, author: str, created: datetime) -> list[dict]:
        """Made up comments of bots and people on an item, not of its author."""
        found = []
        if self.random.random() < 0.4:
            found.append(
                self.node(self.random.choice(BOTS), "NONE", self.when(created, 0.2), "Bot")
            )
        for _ in range(self.random.randint(0, 4)):
            login, association, _ = self.random.choice(PEOPLE)
            if login != author:
                found.append(self.node(login, association, self.when(created, 30)))
        return sorted(found, key=lambda n: n["createdAt"])

    def make(self, count: int, pr: bool) -> list[dict]:
        """Made up pull requests or issues, at made up working hours."""
        found = []
        for number in range(1, count + 1):
            author, association, _ = self.random.choice(PEOPLE)
            # working hours in their part of the world, on any day of the year
            created = START + timedelta(
                days=self.random.uniform(0, 600), hours=self.random.gauss(0, 4)
            )
            comments = self.responses(author, created)
            last = max([created] + [datetime.fromisoformat(c["createdAt"]) for c in comments])
            closed = self.random.random() < 0.7
            item = {
                "id": f"{'pr' if pr else 'issue'}{number}",
                "number": number,
                "title": f"{'Change' if pr else 'Problem'} number {number}",
                "state": "CLOSED" if closed else "OPEN",
                "createdAt": created.isoformat(),
                "updatedAt": last.isoformat(),
                "closedAt": (last + timedelta(hours=1)).isoformat() if closed else None,
                "author": {"login": author, "__typename": "User"},
                "authorAssociation": association,
                "comments": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": comments,
                },
            }
            if pr:
                reviewer, role, _ = self.random.choice(PEOPLE[:3])
                reviews = (
                    []
                    if reviewer == author
                    else [self.node(reviewer, role, self.when(created, 20), key="submittedAt")]
                )
                item.update(
                    merged=closed and self.random.random() < 0.8,
                    mergedAt=None,
                    mergedBy={"login": reviewer} if closed else None,
                    reviews={
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                        "nodes": reviews,
                    },
                )
            found.append(item)
        return found

    def make_commits(self, count: int) -> list[dict]:
        """Made up commits of the first people, newest first."""
        found = []
        for number in range(count):
            login, _, _ = self.random.choice(PEOPLE[:5])
            at = START + timedelta(days=self.random.uniform(0, 600), hours=self.random.gauss(0, 4))
            found.append(
                {
                    "oid": f"{number:040x}",
                    "committedDate": at.isoformat(),
                    "author": {"name": login.title(), "user": {"login": login}},
                }
            )
        return sorted(found, key=lambda c: c["committedDate"], reverse=True)

    async def graphql(self, query: str, **variables) -> dict:
        """Answer a query of the sync like GitHub would: the commits or a page of items."""
        self.requests += 1
        if "history(first: 100" in query:
            history = {
                "totalCount": len(self.commits),
                "pageInfo": {"hasNextPage": False, "endCursor": None},
                "nodes": self.commits,
            }
            return {"repository": {"defaultBranchRef": {"target": {"history": history}}}}
        field = "pullRequests" if "pullRequests(" in query else "issues"
        nodes = sorted(self.items[field], key=lambda i: i["updatedAt"], reverse=True)
        page = {
            "totalCount": len(nodes),
            "pageInfo": {"hasNextPage": False, "endCursor": None},
            "nodes": nodes,
        }
        return {"repository": {field: page}}

    async def people(self, logins: list[str]) -> dict:
        """The made up names and locations of people."""
        self.requests += 1
        known = {login: location for login, _, location in PEOPLE}
        return {
            login: {
                "login": login,
                "name": login.title(),
                "location": known.get(login, ""),
                "avatarUrl": "",
            }
            for login in logins
        }
