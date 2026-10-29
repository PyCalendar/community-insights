"""A stamp of the data: the same while the data is the same, new as soon as it changes.

django-cachalot notes for each table when it was last written, in the cache that all
processes share (gunicorn workers and the fetch worker). The stamp is made of these times,
so an image or a page drawn from the data can be kept and sent again, with an ETag, until a
table changes. It also holds the hour, because waiting times grow without any change of the
data, and the version of the site, because a new version draws differently.
"""

import hashlib
import time
from collections.abc import Callable

from cachalot import api
from django.conf import settings
from django.core.cache import cache

from . import version

HOUR = 3600
KEEP = 24 * 3600  # seconds a result stays in the cache; a new stamp leaves it unused


def tables() -> list[str]:
    """The tables of the data the site shows: those of its models and their many-to-many.

    Returns:
        The names of the tables, sorted.
    """
    from .models import Item

    app = Item._meta.app_config
    assert app is not None
    return sorted({model._meta.db_table for model in app.get_models(include_auto_created=True)})


def changed(table: str) -> float:
    """When the table was last written, as cachalot noted it.

    A table without a note (a new or cleared cache) gets one now: the stamp only moves on,
    and never back to a stamp that was already used for older data.

    Args:
        table: The name of the table.

    Returns:
        The time, in seconds since 1970.
    """
    # the hints of cachalot give each of *tables_or_models the type of all of them
    last = api.get_last_invalidation(table)  # pyright: ignore[reportArgumentType]
    if not last:
        api.invalidate(table)  # pyright: ignore[reportArgumentType]
        last = api.get_last_invalidation(table)  # pyright: ignore[reportArgumentType]
    return last


def stamp(now: float | None = None) -> str | None:
    """The stamp of the data at this moment.

    Args:
        now: The time in seconds since 1970; the current time if None.

    Returns:
        A hexadecimal hash, or None when cachalot is off, which notes no changes.

    Examples:
        >>> from django.test import override_settings
        >>> with override_settings(CACHALOT_ENABLED=False):
        ...     stamp() is None
        True
    """
    if not settings.CACHALOT_ENABLED:
        return None
    hour = int((time.time() if now is None else now) // HOUR)
    build = version.get()
    parts = [str(build.get(key, "")) for key in ("version", "commit_full", "built")]
    parts.append(str(hour))
    parts += [f"{table}={changed(table)!r}" for table in tables()]
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()


def kept[T](name: str, parts: list, compute: Callable[[], T]) -> T:
    """What compute returns, kept in the cache until the data changes.

    Args:
        name: What is computed, such as ``contributors``.
        parts: Everything else it depends on, as texts or numbers.
        compute: Computes it; called when it is not kept.

    Returns:
        What compute returned, now or before with the same stamp.
    """
    found = stamp()
    if found is None:
        return compute()
    key = "kept:" + hashlib.sha256("\n".join([found, name, *map(str, parts)]).encode()).hexdigest()
    value = cache.get(key)
    if value is None:
        value = compute()
        cache.set(key, value, KEEP)
    return value
