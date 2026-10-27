"""What is read from GitHub.

Each read takes `graphql`, an async function that sends a query: a Client or a TokenPool, so the
reads can be shared. Reads of several batches send them at the same time.
"""

import asyncio

from ..errors import OwnerNotFound, RepositoryNotFound
from . import queries


def batches(items: list, size: int = queries.BATCH) -> list[list]:
    """The items in lists of `size`, for requests about several at once.

    Args:
        items: The items.
        size: How many go into one list.

    Returns:
        The lists, the last one shorter.
    """
    return [items[start : start + size] for start in range(0, len(items), size)]


async def viewer(graphql) -> str:
    """The login of the owner of the token.

    Args:
        graphql: An async function that sends a GraphQL query with its variables and returns
            the data, such as ``Client.graphql`` or ``TokenPool.graphql``.

    Returns:
        The login.
    """
    return (await graphql(queries.VIEWER))["viewer"]["login"]


async def repositories(graphql, owner: str | None = None, limit: int = 300) -> list[dict]:
    """Repositories, most stars first.

    Repositories most stars first: those of the owner of the token (owner None) or of an
    organisation or user; private ones if the token sees them.

    Args:
        graphql: An async function that sends a GraphQL query with its variables and returns
            the data, such as ``Client.graphql`` or ``TokenPool.graphql``.
        owner: An organisation or user; None for the owner of the token.
        limit: How many to read at most.

    Returns:
        The repositories as GitHub answers them.

    Raises:
        OwnerNotFound: If GitHub does not know the owner.
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
    """One repository; RepositoryNotFound if it does not exist or the token cannot see it.

    Args:
        graphql: An async function that sends a GraphQL query with its variables and returns
            the data, such as ``Client.graphql`` or ``TokenPool.graphql``.
        full_name: The repository as ``owner/name``.

    Returns:
        The repository as GitHub answers it.

    Raises:
        RepositoryNotFound: If it does not exist or the token cannot see it.
    """
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

    Args:
        graphql: An async function that sends a GraphQL query with its variables and returns
            the data, such as ``Client.graphql`` or ``TokenPool.graphql``.

    Returns:
        The suggestions, each with a name, a kind and the stars.
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
    """The fields of every repository; None for those the token cannot see.

    Args:
        graphql: An async function that sends a GraphQL query with its variables and returns
            the data, such as ``Client.graphql`` or ``TokenPool.graphql``.
        full_names: The repositories as ``owner/name``.
        fields: The GraphQL fields to read of each.

    Returns:
        The fields of each repository by its name.
    """
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
    """Whether the token can read each repository.

    Args:
        graphql: An async function that sends a GraphQL query with its variables and returns
            the data, such as ``Client.graphql`` or ``TokenPool.graphql``.
        full_names: The repositories as ``owner/name``.

    Returns:
        True or False for each repository by its name.
    """
    found = await each_repository(graphql, full_names, "id")
    return {name: bool(data) for name, data in found.items()}


async def totals(graphql, full_names: list[str]) -> dict[str, tuple[int, int] | None]:
    """(pull requests, issues) of each repository.

    Args:
        graphql: An async function that sends a GraphQL query with its variables and returns
            the data, such as ``Client.graphql`` or ``TokenPool.graphql``.
        full_names: The repositories as ``owner/name``.

    Returns:
        The numbers of each repository by its name, None for those the token cannot see.
    """
    found = await each_repository(
        graphql, full_names, "pullRequests { totalCount } issues { totalCount }"
    )
    return {
        name: (data["pullRequests"]["totalCount"], data["issues"]["totalCount"]) if data else None
        for name, data in found.items()
    }


async def people(graphql, logins: list[str]) -> dict[str, dict | None]:
    """name, location and avatar of a few dozen users in one request.

    Args:
        graphql: An async function that sends a GraphQL query with its variables and returns
            the data, such as ``Client.graphql`` or ``TokenPool.graphql``.
        logins: The logins.

    Returns:
        The profile of each login, None for those GitHub does not know.
    """
    variables = {f"l{i}": login for i, login in enumerate(logins)}
    data = await graphql(queries.people(len(logins)), **variables)
    return {login: data.get(f"u{i}") for i, login in enumerate(logins)}
