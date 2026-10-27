import asyncio
from datetime import datetime

from asgiref.sync import sync_to_async

from ..errors import AllTokensUsedUp, FetchLimitReached
from ..models import Item, Repository
from . import events, store
from .sources import GraphQLSource

PEOPLE_BATCH = 30


async def nothing() -> None:
    """The check and the progress that do nothing.

    Returns:
        None.
    """
    return None


async def together(*coroutines) -> list:
    """Run the coroutines at the same time.

    When one is cancelled or fails, the others are cancelled, so a cancelled fetch stops at
    once. When one reaches a limit, the others finish what they asked for (it is paid for and
    saved) and stop at their next request; then the limit is raised.

    Args:
        *coroutines: The coroutines.

    Returns:
        Their results, in their order.

    Raises:
        Exception: The error of the first that failed, after the others stopped.
    """
    tasks = [asyncio.ensure_future(c) for c in coroutines]
    try:
        return await asyncio.gather(*tasks)
    except (FetchLimitReached, AllTokensUsedUp):
        await asyncio.gather(*tasks, return_exceptions=True)
        raise
    except BaseException:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise


class Syncer:
    """Reads a repository into the database.

    Reads the pull requests, issues and people of a repository into the database,
    asynchronously, from a source (sources/): a client or a token pool is read with GraphQL.
    `on_item()` is awaited after each item, `check()` before each request: it raises
    FetchCancelled to stop. Each item is saved when it was read, so what was read stays when the
    fetch stops; a stopped fetch continues after its last page. The comments of the items of a
    page and the batches of people are read at the same time.
    """

    def __init__(self, source, on_item=nothing, check=nothing):
        """Read repositories into the database.

        Args:
            source: A source (``GraphQLSource``, ``AnonymousSource``) or a client with tokens,
                which is read with GraphQL.
            on_item: Called after each item read, such as for the progress of a job.
            check: Called before each request; raises to stop, such as when the job was cancelled.
        """
        self.source = source if hasattr(source, "page") else GraphQLSource(source)
        self.source.check = check
        self.on_item = on_item

    async def events_of(self, item: dict, kind: str) -> list:
        """The opening, comments and reviews of an item, with the pages after the first.

        Args:
            item: The item as GitHub answered it.
            kind: ``pr`` or ``issue``.

        Returns:
            The events, not saved yet.
        """
        fields = ["comments"] + (["reviews"] if kind == Item.PR else [])
        pages = await together(*(self.source.all_nodes(item, field) for field in fields))
        found = events.opened(item)
        for field, nodes in zip(fields, pages, strict=True):
            found += events.responses(nodes, field)
        return found

    async def sync_kind(self, repository: Repository, kind: str) -> int:
        """Read the items changed since the last time, newest change first.

        Args:
            repository: The repository.
            kind: ``pr`` or ``issue``.

        Returns:
            How many items were read.
        """
        stop = repository.prs_synced_until if kind == Item.PR else repository.issues_synced_until
        newest, count, cursor, total = stop, 0, None, None
        resumed, resumed_stop, resumed_newest = store.progress_of(repository, kind)
        if resumed:
            cursor, stop, newest = resumed, resumed_stop, resumed_newest
        replace = self.source.replaces_events
        while True:
            page = await self.source.page(repository, kind, cursor, stop)
            total = page.get("totalCount", total)
            changed = []
            for data in page["nodes"]:
                if stop and datetime.fromisoformat(data["updatedAt"]) <= stop:
                    break
                changed.append(data)
            found = await together(*(self.events_of(data, kind) for data in changed))
            await sync_to_async(store.save_items)(
                repository, kind, list(zip(changed, found, strict=True)), replace
            )
            for data in changed:
                await self.on_item()
                count += 1
                updated = datetime.fromisoformat(data["updatedAt"])
                newest = max(newest, updated) if newest else updated
            if len(changed) < len(page["nodes"]) or not page["pageInfo"]["hasNextPage"]:
                break
            cursor = page["pageInfo"]["endCursor"]
            await sync_to_async(store.save_progress)(repository, kind, cursor, stop, newest)
        await sync_to_async(store.finish_kind)(repository, kind, newest, total)
        return count

    async def sync_commits(self, repository: Repository) -> int:
        """The commits of the default branch since the last fetch.

        Args:
            repository: The repository.

        Returns:
            How many commits were read.
        """
        since = repository.commits_synced_until
        newest, cursor, count, total = since, None, 0, None
        while True:
            page = await self.source.commits(repository, cursor, since)
            total = page["total"] if page["total"] is not None else total
            nodes = [
                n for n in page["nodes"] if not since or datetime.fromisoformat(n["at"]) > since
            ]
            await sync_to_async(store.save_commits)(repository, nodes)
            count += len(nodes)
            for node in nodes:
                at = datetime.fromisoformat(node["at"])
                newest = max(newest, at) if newest else at
            if not page["next"]:
                break
            cursor = page["next"]
        await sync_to_async(store.finish_commits)(repository, newest, total)
        return count

    async def sync_people(self, repository: Repository) -> None:
        """Name, location and avatar of the actors that are new or old.

        Args:
            repository: The repository.
        """
        todo = await sync_to_async(store.people_to_read)(repository)
        batches = [todo[i : i + PEOPLE_BATCH] for i in range(0, len(todo), PEOPLE_BATCH)]

        async def read(batch):
            await sync_to_async(store.save_people)(await self.source.people(batch))

        await together(*(read(batch) for batch in batches))

    async def sync(self, repository: Repository) -> str:
        """Read the pull requests, issues and people; a summary.

        Args:
            repository: The repository.

        Returns:
            How many pull requests, issues and commits were read.
        """
        prs, issues, commits = await together(
            self.sync_kind(repository, Item.PR),
            self.sync_kind(repository, Item.ISSUE),
            self.sync_commits(repository),
        )
        await self.sync_people(repository)
        return f"{prs} pull requests, {issues} issues and {commits} commits read"
