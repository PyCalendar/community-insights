import niquests
from django.conf import settings

from ..errors import (
    AllTokensUsedUp,
    GitHubRequestRejected,
    GitHubUnreachable,
    RateLimitExceeded,
    RepositoryNotFound,
)
from . import limits
from .rate import RateLimit

PER_PAGE = 100
# GitHub counts requests without a token per IP address: one quota for everybody
# on this server, as GitHub told in its last answer.
SERVER_QUOTA = RateLimit()


class AnonymousClient:
    """Reads public repositories with the REST API without a token.

    Reads public repositories with the REST API without a token: 60 requests per hour for this
    server's IP address, shared by everybody without a token.
    """

    def __init__(self, api: str | None = None):
        self.api = (api or settings.GITHUB_API).rstrip("/")
        self.session = niquests.AsyncSession(
            hooks=niquests.AsyncLeakyBucketLimiter(rate=limits.POINTS_PER_SECOND)
        )
        self.session.headers["Accept"] = "application/vnd.github+json"
        self.session.headers["User-Agent"] = "community-insights"
        self.rate = SERVER_QUOTA
        self.requests = 0

    async def get(self, path: str, **params):
        """A REST answer as JSON, without a token.

        A REST answer as JSON, without a token; the quota of the server is noted and
        respected.
        """
        if self.rate.remaining == 0 and self.rate.reset_at:
            again = f"{self.rate.reset_at:%H:%M} UTC"
            raise AllTokensUsedUp(
                f"The requests without a token can be made again at {again}.", self.rate.reset_at
            )
        async with limits.server_slots():
            self.requests += 1
            try:
                response = await self.session.get(f"{self.api}{path}", params=params, timeout=60)
            except niquests.RequestException as error:
                raise GitHubUnreachable(str(error)) from error
        if "/search/" not in path:  # the search has a quota of its own
            self.rate.note(response.headers or {})
        status = response.status_code
        if status is None:
            raise GitHubUnreachable(f"GitHub gave no answer to {path}.")
        if status in (403, 429) and (
            self.rate.remaining == 0 or "rate limit" in (response.text or "").lower()
        ):
            raise RateLimitExceeded("The requests without a token are used up.", self.rate.reset_at)
        if status == 404:
            raise RepositoryNotFound(f"{path} was not found, or it is not public.")
        if status >= 500:
            raise GitHubUnreachable(f"GitHub answered {status}.")
        if status >= 400:
            raise GitHubRequestRejected(
                f"GitHub answered {status}: {(response.text or '')[:200]}", status=status
            )
        return response.json()

    async def all_pages(self, path: str, **params) -> list[dict]:
        """All pages of a REST list, 100 at a time."""
        found, page = [], 1
        while True:
            answer = await self.get(path, per_page=PER_PAGE, page=page, **params)
            found += answer
            if len(answer) < PER_PAGE:
                return found
            page += 1

    async def close(self) -> None:
        """Close the connections."""
        await self.session.close()

    # the reads of reads.py that work without a token, in the same shape

    @staticmethod
    def shape(repo: dict) -> dict:
        """A repository of the REST API in the shape of the GraphQL answers."""
        return {
            "nameWithOwner": repo["full_name"],
            "description": repo.get("description") or "",
            "stargazerCount": repo.get("stargazers_count", 0),
            "isPrivate": repo.get("private", False),
            "isArchived": repo.get("archived", False),
        }

    async def repository(self, full_name: str) -> dict:
        """A public repository, in the shape of the GraphQL answers."""
        return self.shape(await self.get(f"/repos/{full_name}"))

    async def repositories(self, owner: str, limit: int = 300) -> list[dict]:
        """The public repositories of an owner, most stars first."""
        found = await self.all_pages(f"/users/{owner}/repos", sort="updated")
        return sorted((self.shape(r) for r in found), key=lambda r: -r["stargazerCount"])[:limit]

    async def totals(self, full_names: list[str]) -> dict[str, tuple[int, int] | None]:
        """Pull requests and issues of each repository, with the search."""
        found = {}
        for name in full_names:
            try:
                prs = await self.get("/search/issues", q=f"repo:{name} is:pr", per_page=1)
                issues = await self.get("/search/issues", q=f"repo:{name} is:issue", per_page=1)
            except RepositoryNotFound:
                found[name] = None
                continue
            except GitHubRequestRejected as error:
                if error.context.get("status") == 422:  # the search does not know it
                    found[name] = None
                    continue
                raise
            found[name] = (prs["total_count"], issues["total_count"])
        return found
