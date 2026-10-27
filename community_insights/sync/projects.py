from asgiref.sync import sync_to_async
from django.conf import settings
from django.utils.translation import gettext

from ..errors import (
    InvalidTarget,
    NoPublicRepositories,
    PrivateRepositoryRefused,
    RepositoryNotFound,
)
from ..models import Project, Repository
from .store import store_repository


def clean_target(target: str) -> str:
    """owner/name or owner, from what people type or paste.

    Args:
        target: The text, such as ``https://github.com/django/django/``.

    Returns:
        ``owner/name`` or ``owner``.

    Raises:
        InvalidTarget: If it is neither.
    """
    cleaned = (target or "").strip().strip("/").removeprefix("https://github.com/")
    if cleaned.count("/") > 1 or not cleaned:
        raise InvalidTarget(
            gettext("%(target)s is not owner/name or owner.") % {"target": repr(target)}
        )
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

    Args:
        target: ``owner/name`` or ``owner``.
        found: The repositories GitHub answered.

    Returns:
        The repositories to add.

    Raises:
        PrivateRepositoryRefused: If the repository is private.
        NoPublicRepositories: If the owner has no public repositories.
    """
    if settings.PRIVATE_REPOSITORIES:
        return found
    public = [r for r in found if not r.get("isPrivate")]
    if "/" in target and not public:
        raise PrivateRepositoryRefused(gettext("%(target)s is private.") % {"target": target})
    if not public:
        raise NoPublicRepositories(
            gettext("%(target)s has no public repositories.") % {"target": target}
        )
    return public


def not_found(target: str) -> RepositoryNotFound:
    """The error for a repository that is private to others: the same as for a missing one.

    Args:
        target: The repository as ``owner/name``.

    Returns:
        The error, to raise.
    """
    return RepositoryNotFound(
        gettext("%(target)s was not found, or the token cannot see it.") % {"target": target}
    )


async def own_view(found: list[dict], own) -> list[dict]:
    """The repositories without the private ones that only tokens of others can see.

    Tokens shared by others, or donated to the site, can see private repositories of their
    owners. Whether such a repository exists must not be told to somebody else: it is left
    out, as if it did not exist. A private repository stays when a token of the person can
    see it.

    Args:
        found: The repositories as GitHub answered them, with ``isPrivate``.
        own: A reader with only the tokens of the person (``visible``), None without any.

    Returns:
        The repositories the person may know of.
    """
    private = [r["nameWithOwner"] for r in found if r.get("isPrivate")]
    if not private:
        return found
    seen = await own.visible(private) if own is not None else {}
    return [r for r in found if not r.get("isPrivate") or seen.get(r["nameWithOwner"])]


async def add_public(reader, target: str) -> list[Repository]:
    """Store public repositories somebody without an account submitted.

    Args:
        reader: The donated tokens of the site, or the client without a token.
        target: owner/name or owner, as typed or pasted.

    Returns:
        The stored public repositories.

    Raises:
        InvalidTarget: If it is no repository or owner.
        RepositoryNotFound: If the repository does not exist or is private: a visitor has no
            token, so a private repository is not told apart from a missing one.
        NoPublicRepositories: If the owner has no public repositories.
    """
    target = clean_target(target)
    found = (
        [await reader.repository(target)] if "/" in target else await reader.repositories(target)
    )
    public = [r for r in found if not r.get("isPrivate")]
    if "/" in target and not public:
        raise not_found(target)
    if not public:
        raise NoPublicRepositories(
            gettext("%(target)s has no public repositories.") % {"target": target}
        )
    return await sync_to_async(lambda: [store_repository(r) for r in public])()


async def add_project(user, client, target: str, is_private: bool = False, own=None) -> Project:
    """Create the project, with the repositories the tokens can see.

    Args:
        user: The user who gets the project.
        client: The tokens to read with: the own ones, then those others share.
        target: ``owner/name`` or ``owner``, as typed or pasted.
        is_private: Whether the project is private.
        own: A reader with only the tokens of the user, None without any: a private
            repository is only known when one of them can see it.

    Returns:
        The project.

    Raises:
        InvalidTarget: If it is no repository or owner.
        RepositoryNotFound: If the repository does not exist, or only tokens of others see it.
        PrivateRepositoryRefused: If the repository is private and a token of the user sees it.
        NoPublicRepositories: If the owner has no public repositories.
    """
    target = clean_target(target)
    if "/" in target:
        found = [await client.repository(target)]
    else:
        found = await client.repositories(target)
    found = await own_view(found, own)
    if "/" in target and not found:
        raise not_found(target)
    return await save_project(user, target, allowed(target, found), is_private)
