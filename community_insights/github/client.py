import asyncio

import niquests
from django.conf import settings

from ..errors import GitHubUnreachable, SecondaryRateLimitExceeded
from . import limits, reads
from .answers import data_of
from .headers import header_int
from .rate import RateLimit


class Client:
    """Sends GraphQL queries to GitHub with one token, asynchronously, and remembers its rate limit.

    The reads of reads.py are its methods, too.
    """

    def __init__(self, token: str, api: str | None = None):
        """Read GitHub with one token.

        Args:
            token: The token.
            api: The address of the API, ``GITHUB_API`` if None.
        """
        self.token = token
        self.api = (api or settings.GITHUB_API).rstrip("/")
        # an even pace below the points per minute of GitHub
        self.session = niquests.AsyncSession(
            hooks=niquests.AsyncLeakyBucketLimiter(rate=limits.POINTS_PER_SECOND)
        )
        self.slots: asyncio.Semaphore | None = None  # requests of this token at once
        self.session.headers["Authorization"] = f"Bearer {token}"
        self.session.headers["User-Agent"] = "community-insights"
        self.rate = RateLimit()
        self.requests = 0  # one API point each for the queries used here

    async def graphql(self, query: str, **variables) -> dict:
        """The data of a query.

        When GitHub asks to slow down, wait as long as it asks and try again; longer waits
        are left to the caller.

        Args:
            query: The GraphQL query.
            **variables: Its variables.

        Returns:
            The data of the answer.

        Raises:
            SecondaryRateLimitExceeded: If GitHub asks to wait longer than ``limits.MAX_WAIT``, or
                still after ``limits.RETRIES`` tries.
            AssertionError: Never: the loop returns or raises before.
        """
        for attempt in range(limits.RETRIES + 1):
            try:
                return await self.send(query, variables)
            except SecondaryRateLimitExceeded as error:
                wait = limits.backoff(attempt, error.retry_after)
                if attempt == limits.RETRIES or wait > limits.MAX_WAIT:
                    raise
                await asyncio.sleep(wait)
        raise AssertionError("not reached")

    async def send(self, query: str, variables: dict) -> dict:
        """Send one query: within the limits of the token and the server, noting the rate limit.

        Args:
            query: The GraphQL query.
            variables: Its variables.

        Returns:
            The data of the answer.

        Raises:
            GitHubUnreachable: If GitHub cannot be reached.
            TokenError: If GitHub refuses the token (see ``answers.check``).
            GitHubError: If GitHub answers with another error.
        """
        if self.slots is None:
            self.slots = asyncio.Semaphore(limits.PER_TOKEN)
        async with limits.server_slots(), self.slots:
            self.requests += 1
            try:
                response = await self.session.post(
                    f"{self.api}/graphql",
                    json={"query": query, "variables": variables},
                    timeout=60,
                )
            except niquests.RequestException as error:
                raise GitHubUnreachable(str(error)) from error
        if response.status_code is None:
            raise GitHubUnreachable("GitHub gave no answer.")
        headers = response.headers or {}
        self.rate.note(headers)
        try:
            body = response.json()
        except ValueError as error:
            body = error
        return data_of(
            response.status_code,
            response.text or "",
            body,
            self.rate,
            header_int(headers, "retry-after"),
        )

    async def close(self) -> None:
        """Close the connections."""
        await self.session.close()

    async def viewer(self):
        """The login of the owner of the token (reads.viewer).

        Returns:
            The login.
        """
        return await reads.viewer(self.graphql)

    async def repositories(self, owner=None, limit=300):
        """Repositories most stars first (reads.repositories).

        Args:
            owner: An organisation or user; None for the owner of the token.
            limit: How many to read at most.

        Returns:
            The repositories as GitHub answers them.
        """
        return await reads.repositories(self.graphql, owner, limit)

    async def repository(self, full_name):
        """One repository (reads.repository).

        Args:
            full_name: The repository as ``owner/name``.

        Returns:
            The repository as GitHub answers it.
        """
        return await reads.repository(self.graphql, full_name)

    async def suggestions(self):
        """Repositories and organisations to offer (reads.suggestions).

        Returns:
            The suggestions, each with a name, a kind and the stars.
        """
        return await reads.suggestions(self.graphql)

    async def visible(self, full_names):
        """Whether the token can read each repository (reads.visible).

        Args:
            full_names: The repositories as ``owner/name``.

        Returns:
            True or False for each repository by its name.
        """
        return await reads.visible(self.graphql, full_names)

    async def totals(self, full_names):
        """Pull requests and issues of each repository (reads.totals).

        Args:
            full_names: The repositories as ``owner/name``.

        Returns:
            The pull requests and issues of each repository, None for those not seen.
        """
        return await reads.totals(self.graphql, full_names)

    async def people(self, logins):
        """Name, location and avatar of people (reads.people).

        Args:
            logins: The logins.

        Returns:
            The profile of each login, None for those GitHub does not know.
        """
        return await reads.people(self.graphql, logins)
