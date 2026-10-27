"""Writing what was read into the database.

Everything here is synchronous; the async Syncer calls it with sync_to_async.
"""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from ..models import Commit, Event, Item, Person, Repository
from .events import is_bot

PEOPLE_MAX_AGE = timedelta(days=30)


def store_repository(data: dict) -> Repository:
    """Store or update a repository of a GraphQL answer."""
    owner = data["nameWithOwner"].split("/")[0]
    repository, _ = Repository.objects.update_or_create(
        full_name=data["nameWithOwner"],
        defaults={
            "owner_login": owner,
            "description": data.get("description") or "",
            "stars": data.get("stargazerCount", 0),
            "is_private": data.get("isPrivate", False),
            "is_archived": data.get("isArchived", False),
            "fetched_at": timezone.now(),
        },
    )
    return repository


@transaction.atomic
def save_item(
    repository: Repository, kind: str, data: dict, events: list[Event], replace: bool = True
) -> None:
    """Store an item with its events.

    An item with its events: replacing those stored, or added to them (without the ones stored
    already) when only new events were read.
    """
    author = data.get("author") or {}
    item, _ = Item.objects.update_or_create(
        repository=repository,
        kind=kind,
        number=data["number"],
        defaults={
            "node_id": data["id"],
            "title": data["title"][:500],
            "author": author.get("login", ""),
            "author_association": (data.get("authorAssociation") or "").lower(),
            "author_is_bot": bool(author.get("login"))
            and is_bot(author["login"], author.get("__typename")),
            "state": data["state"].lower() if data["state"] == "OPEN" else "closed",
            "merged": bool(data.get("merged")),
            "created_at": parse_datetime(data["createdAt"]),
            "updated_at": parse_datetime(data["updatedAt"]),
            "closed_at": parse_datetime(data["closedAt"]) if data.get("closedAt") else None,
            "merged_by": (data.get("mergedBy") or {}).get("login", ""),
        },
    )
    if replace:
        item.events.all().delete()
    else:
        known = set(item.events.values_list("actor", "kind", "at"))
        events = [e for e in events if (e.actor, e.kind, e.at) not in known]
    for event in events:
        event.item = item
    Event.objects.bulk_create(events)


def save_progress(repository: Repository, kind: str, cursor: str, stop, newest) -> None:
    """After a page: a fetch that stops continues after it the next time."""
    repository.resume[kind] = {
        "cursor": cursor,
        "stop": stop.isoformat() if stop else None,
        "newest": newest.isoformat() if newest else None,
    }
    repository.save(update_fields=["resume"])


def progress_of(repository: Repository, kind: str) -> tuple:
    """(cursor, stop, newest) of a stopped fetch, or (None, None, None)."""
    found = repository.resume.get(kind)
    if not found:
        return None, None, None
    return (
        found["cursor"],
        parse_datetime(found["stop"]) if found["stop"] else None,
        parse_datetime(found["newest"]) if found["newest"] else None,
    )


@transaction.atomic
def save_items(repository: Repository, kind: str, found: list[tuple], replace: bool) -> None:
    """The items of a page with their events, in one transaction."""
    for data, events in found:
        save_item(repository, kind, data, events, replace)


@transaction.atomic
def save_commits(repository: Repository, nodes: list[dict]) -> None:
    """Commits of a page; those stored already stay."""
    Commit.objects.bulk_create(
        [
            Commit(
                repository=repository,
                sha=n["sha"],
                author=n["login"],
                author_name=n["name"][:200],
                at=parse_datetime(n["at"]),
            )
            for n in nodes
        ],
        ignore_conflicts=True,
    )


def finish_commits(repository: Repository, newest, total: int | None) -> None:
    """Remember up to when the commits were read, and how many there are."""
    repository.commits_synced_until = newest or timezone.now()
    if total is not None:
        repository.commits_total = total
    repository.save(update_fields=["commits_synced_until", "commits_total"])


def finish_kind(repository: Repository, kind: str, newest, total: int | None) -> None:
    """Remember up to which change the kind was read, and how many there are.

    Nothing there yet: it was read completely now.
    """
    repository.resume.pop(kind, None)
    if kind == Item.PR:
        repository.prs_synced_until = newest or timezone.now()
        repository.prs_total = total if total is not None else repository.prs_total
    else:
        repository.issues_synced_until = newest or timezone.now()
        repository.issues_total = total if total is not None else repository.issues_total
    repository.fetched_at = timezone.now()
    repository.save()


def people_to_read(repository: Repository) -> list[str]:
    """The actors whose name and location are unknown or old.

    Bots are stored as bots and not read.
    """
    logins = set(Event.objects.filter(item__repository=repository).values_list("actor", flat=True))
    known = {p.login: p for p in Person.objects.filter(login__in=logins)}
    bots = set(Event.objects.filter(actor__in=logins, is_bot=True).values_list("actor", flat=True))
    limit = timezone.now() - PEOPLE_MAX_AGE
    todo = []
    for login in sorted(logins):
        person = known.get(login)
        if person and person.fetched_at and person.fetched_at > limit:
            continue
        if login in bots:
            Person.objects.update_or_create(
                login=login, defaults={"is_bot": True, "fetched_at": timezone.now()}
            )
        else:
            todo.append(login)
    return todo


def save_people(found: dict[str, dict | None]) -> None:
    """Store the names, locations and avatars read."""
    for login, data in found.items():
        Person.objects.update_or_create(
            login=login,
            defaults={
                "name": (data or {}).get("name") or "",
                "location": (data or {}).get("location") or "",
                "avatar_url": (data or {}).get("avatarUrl") or "",
                "fetched_at": timezone.now(),
            },
        )
