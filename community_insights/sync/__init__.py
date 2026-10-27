"""Reading repositories from GitHub into the database."""

from asgiref.sync import async_to_sync

from ..errors import FetchCancelled
from .events import is_bot
from .projects import add_project, add_public, clean_target
from .queries import FIELDS, INNER, PAGE, list_query, more_query
from .store import PEOPLE_MAX_AGE, store_repository
from .syncer import PEOPLE_BATCH, Syncer

Cancelled = FetchCancelled  # the user cancelled the fetch; what was read stays


def read_repository(client, repository) -> str:
    """Read a repository now, from synchronous code; a summary."""
    return async_to_sync(Syncer(client).sync)(repository)


__all__ = [
    "FIELDS",
    "INNER",
    "PAGE",
    "PEOPLE_BATCH",
    "PEOPLE_MAX_AGE",
    "Cancelled",
    "Syncer",
    "add_project",
    "add_public",
    "clean_target",
    "is_bot",
    "list_query",
    "more_query",
    "read_repository",
    "store_repository",
]
