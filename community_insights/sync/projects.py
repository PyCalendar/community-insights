from asgiref.sync import sync_to_async
from django.conf import settings

from ..errors import InvalidTarget, NoPublicRepositories, PrivateRepositoryRefused
from ..models import Project, Repository
from .store import store_repository


def clean_target(target: str) -> str:
    """owner/name or owner, from what people type or paste."""
    cleaned = (target or "").strip().strip("/").removeprefix("https://github.com/")
    if cleaned.count("/") > 1 or not cleaned:
        raise InvalidTarget(f"{target!r} is not owner/name or owner.")
    return cleaned


@sync_to_async
def save_project(user, target: str, found: list[dict], is_private: bool) -> Project:
    """Store the project with its repositories."""
    project, _ = Project.objects.get_or_create(
        user=user, target=found[0]["nameWithOwner"] if "/" in target else target
    )
    project.is_private = is_private or any(r.get("isPrivate") for r in found)
    project.save()
    project.repositories.set([store_repository(r) for r in found])
    return project


def allowed(target: str, found: list[dict]) -> list[dict]:
    """The repositories that may be added: for now only public ones.

    For now only public repositories: a private one is refused, of an organisation only the
    public ones are kept (PRIVATE_REPOSITORIES).
    """
    if settings.PRIVATE_REPOSITORIES:
        return found
    public = [r for r in found if not r.get("isPrivate")]
    if "/" in target and not public:
        raise PrivateRepositoryRefused(f"{target} is private.")
    if not public:
        raise NoPublicRepositories(f"{target} has no public repositories.")
    return public


async def add_public(reader, target: str) -> list[Repository]:
    """Store public repositories somebody without an account submitted.

    Args:
        reader: The donated tokens of the site, or the client without a token.
        target: owner/name or owner, as typed or pasted.

    Returns:
        The stored public repositories.

    Raises:
        InvalidTarget: If it is no repository or owner.
        PrivateRepositoryRefused: If the repository is private.
        NoPublicRepositories: If the owner has no public repositories.
    """
    target = clean_target(target)
    found = (
        [await reader.repository(target)] if "/" in target else await reader.repositories(target)
    )
    public = [r for r in found if not r.get("isPrivate")]
    if "/" in target and not public:
        raise PrivateRepositoryRefused(f"{target} is private.")
    if not public:
        raise NoPublicRepositories(f"{target} has no public repositories.")
    return await sync_to_async(lambda: [store_repository(r) for r in public])()


async def add_project(user, client, target: str, is_private: bool = False) -> Project:
    """Create the project, with the repositories the token can see."""
    target = clean_target(target)
    if "/" in target:
        found = [await client.repository(target)]
    else:
        found = await client.repositories(target)
    return await save_project(user, target, allowed(target, found), is_private)
