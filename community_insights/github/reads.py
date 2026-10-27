"""What is read from GitHub.

Each read takes `graphql`, an async function that sends a query: a Client or a TokenPool, so the
reads can be shared. Reads of several batches send them at the same time.
"""

import asyncio

from ..errors import OwnerNotFound, RepositoryNotFound
from . import queries


def batches(items: list, size: int = queries.BATCH) -> list[list]:
    """The items in lists of `size`, for requests about several at once."""
    return [items[start : start + size] for start in range(0, len(items), size)]


async def viewer(graphql) -> str:
    """The login of the owner of the token."""
    return (await graphql(queries.VIEWER))["viewer"]["login"]


async def repositories(graphql, owner: str | None = None, limit: int = 300) -> list[dict]:
    """Repositories, most stars first.

    Repositories most stars first: those of the owner of the token (owner None) or of an
    organisation or user; private ones if the token sees them.
    """
    query = queries.repositories(owner)
    found, after = [], None
    while len(found) < limit:
        data = await graphql(query, login=owner or "", after=after)
        owner_data = data.get("viewer") or data.get("repositoryOwner")
        if owner_data is None:
            raise OwnerNotFound(f"{owner} was not found on GitHub.")
        page = owner_data["repositories"]
        found += page["nodes"]
        if not page["pageInfo"]["hasNextPage"]:
            break
        after = page["pageInfo"]["endCursor"]
    return found


async def repository(graphql, full_name: str) -> dict:
    """One repository; RepositoryNotFound if it does not exist or the token cannot see it."""
    owner, name = full_name.split("/", 1)
    data = await graphql(queries.REPOSITORY, owner=owner, name=name)
    if not data.get("repository"):
        raise RepositoryNotFound(f"{full_name} was not found, or the token cannot see it.")
    return data["repository"]


async def suggestions(graphql) -> list[dict]:
    """What the owner of the token is likely to look at.

    What the owner of the token is likely to look at, most stars first: their organisations,
    their repositories, those of their organisations and those they contributed to. [{"name",
    "kind", "stars"}]
    """
    data = (await graphql(queries.SUGGESTIONS))["viewer"]
    found: dict[str, dict] = {}

    def add(name, kind, stars=0):
        found.setdefault(name.lower(), {"name": name, "kind": kind, "stars": stars})

    for organisation in data["organizations"]["nodes"]:
        add(organisation["login"], "organisation")
    from django.conf import settings

    def shown(repo) -> bool:  # for now only public repositories
        return settings.PRIVATE_REPOSITORIES or not repo.get("isPrivate")

    for repo in filter(shown, data["repositories"]["nodes"]):
        add(repo["nameWithOwner"], "yours", repo["stargazerCount"])
    for organisation in data["organizations"]["nodes"]:
        for repo in filter(shown, organisation["repositories"]["nodes"]):
            add(repo["nameWithOwner"], "organisation", repo["stargazerCount"])
    for repo in filter(shown, data["repositoriesContributedTo"]["nodes"]):
        add(repo["nameWithOwner"], "contributed", repo["stargazerCount"])
    return list(found.values())


async def each_repository(graphql, full_names: list[str], fields: str) -> dict[str, dict | None]:
    """The fields of every repository; None for those the token cannot see."""
    parts = batches(full_names)
    answers = await asyncio.gather(
        *(graphql(queries.each_repository(part, fields)) for part in parts)
    )
    return {
        name: data.get(f"r{i}")
        for part, data in zip(parts, answers, strict=True)
        for i, name in enumerate(part)
    }


async def visible(graphql, full_names: list[str]) -> dict[str, bool]:
    """Whether the token can read each repository."""
    found = await each_repository(graphql, full_names, "id")
    return {name: bool(data) for name, data in found.items()}


async def totals(graphql, full_names: list[str]) -> dict[str, tuple[int, int] | None]:
    """(pull requests, issues) of each repository."""
    found = await each_repository(
        graphql, full_names, "pullRequests { totalCount } issues { totalCount }"
    )
    return {
        name: (data["pullRequests"]["totalCount"], data["issues"]["totalCount"]) if data else None
        for name, data in found.items()
    }


async def people(graphql, logins: list[str]) -> dict[str, dict | None]:
    """name, location and avatar of a few dozen users in one request."""
    variables = {f"l{i}": login for i, login in enumerate(logins)}
    data = await graphql(queries.people(len(logins)), **variables)
    return {login: data.get(f"u{i}") for i, login in enumerate(logins)}
