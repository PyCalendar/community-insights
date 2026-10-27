from asgiref.sync import sync_to_async
from django.utils import timezone

from ..errors import (
    AllTokensUsedUp,
    ExpiredAPIToken,
    FetchLimitReached,
    NoGitHubAccess,
    RateLimitExceeded,
    TokenError,
)
from ..github import reads
from .entry import HOUR, Entry


class TokenPool:
    """Sends every query with the first usable token, like a client.

    A token that reached its limit or GitHub's is skipped until it can be used again; a rejected
    or expired one is not used again. The reads of github/reads.py are its methods, too, so each
    of their requests can use another token.
    """

    def __init__(self, entries: list[Entry], point_limit: int | None = None):
        """Use the first usable token of several, the next one when it is used up.

        Args:
            entries: The tokens, in the order they are used.
            point_limit: The most API points this pool may use, None for no limit.

        Raises:
            NoGitHubAccess: If there is no token.
        """
        if not entries:
            raise NoGitHubAccess(
                "Link your GitHub account or add a token on the page GitHub access."
            )
        self.entries = entries
        self.point_limit = point_limit
        self.points = 0

    def current(self) -> Entry:
        """The first token that may be used now; AllTokensUsedUp with when, if none.

        Returns:
            The first token that may be used now.

        Raises:
            AllTokensUsedUp: If none may be used now; it says when one may be used again.
        """
        now = timezone.now()
        for entry in self.entries:
            if entry.usable(now):
                return entry
        reset = min(entry.available_again(now) for entry in self.entries)
        raise AllTokensUsedUp(f"The tokens can be used again at {reset:%H:%M} UTC.", reset)

    async def drop(self, entry: Entry, error: TokenError) -> None:
        """Do not use a token that does not work; the last error is raised.

        Args:
            entry: The token that does not work.
            error: Why it does not work.

        Raises:
            TokenError: The error, if no token is left.
        """
        await sync_to_async(entry.spent)(timezone.now(), error)
        self.entries = [e for e in self.entries if e is not entry]
        if not self.entries:
            raise error

    async def graphql(self, query: str, **variables) -> dict:
        """Send a query with the first usable token, skipping used up and rejected ones.

        Args:
            query: The GraphQL query.
            **variables: Its variables.

        Returns:
            The data of the answer.

        Raises:
            FetchLimitReached: If the pool used its limit of points.
            AllTokensUsedUp: If no token may be used now.
            TokenError: If no token works.
        """
        if self.point_limit is not None and self.points >= self.point_limit:
            raise FetchLimitReached(f"The limit of {self.point_limit} API points is reached.")
        while True:
            entry = self.current()
            if entry.expired(timezone.now()):
                assert entry.stored is not None  # only stored tokens expire
                expired = entry.stored.expires_at
                await self.drop(
                    entry, ExpiredAPIToken(f"{entry.label} expired on {expired:%Y-%m-%d}.")
                )
                continue
            try:
                data = await entry.client.graphql(query, **variables)
            except RateLimitExceeded as error:
                entry.client.rate.remaining = 0
                entry.client.rate.reset_at = error.reset_at or timezone.now() + HOUR
                await sync_to_async(entry.spent)(timezone.now(), error)
                continue
            except TokenError as error:
                await self.drop(entry, error)
                continue
            self.points += 1
            await sync_to_async(entry.spent)(timezone.now())
            return data

    async def close(self) -> None:
        """Close the connections of all tokens."""
        for entry in self.entries:
            close = getattr(entry.client, "close", None)
            if close:
                await close()

    async def viewer(self):
        """The login of the owner of the first token (reads.viewer).

        Returns:
            The login.
        """
        return await reads.viewer(self.graphql)

    async def repositories(self, owner=None, limit=300):
        """Repositories most stars first (reads.repositories).

        Args:
            owner: An organisation or user; None for the owner of the first token.
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
        """Whether the tokens can read each repository (reads.visible).

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
