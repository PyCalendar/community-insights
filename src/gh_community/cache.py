"""A disk cache for GitHub API responses, validated with ETags.

Every GET request goes through the cache. A cached response is revalidated
with If-None-Match. GitHub answers 304 Not Modified without counting the
request against the rate limit, so repeating an analysis uses no API calls
for the data that did not change.
"""

import hashlib
import json
import os
import tempfile
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from github.Requester import (
    HTTPRequestsConnectionClass,
    HTTPSRequestsConnectionClass,
    Requester,
)


def default_cache_dir() -> Path:
    """A private directory per user in the temporary directory."""
    return Path(tempfile.gettempdir()) / f"gh-community-cache-{os.getuid()}"


@dataclass
class CacheStats:
    cached: int = 0  # revalidated with 304: no API calls used
    fetched: int = 0  # downloaded: counts against the rate limit


class ResponseCache:
    """Cached responses as JSON files, only readable by the current user."""

    def __init__(self, directory: Path | None = None) -> None:
        self.directory = Path(directory or default_cache_dir())
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self.directory.stat().st_uid != os.getuid():
            raise PermissionError(f"{self.directory} is owned by another user.")
        self.directory.chmod(0o700)
        self.stats = CacheStats()
        self._lock = threading.Lock()

    def count(self, cached: bool) -> None:
        with self._lock:
            if cached:
                self.stats.cached += 1
            else:
                self.stats.fetched += 1

    def key(self, authorization: str, location: str) -> str:
        """Responses depend on the token: it may see more than another one."""
        return hashlib.sha256(f"{authorization}\n{location}".encode()).hexdigest()

    def recall(self, key: str):
        """A value remembered with remember(), or None."""
        entry = self.load(key)
        return entry["value"] if entry and "value" in entry else None

    def remember(self, key: str, value) -> None:
        self.store(key, {"value": value})

    def load(self, key: str) -> dict | None:
        try:
            return json.loads((self.directory / f"{key}.json").read_text())
        except (OSError, ValueError):
            return None

    def store(self, key: str, entry: dict) -> None:
        path = self.directory / f"{key}.json"
        temporary = path.with_suffix(f".{os.getpid()}.{threading.get_ident()}.tmp")
        temporary.touch(mode=0o600)
        temporary.write_text(json.dumps(entry))
        temporary.replace(path)


class CachedResponse:
    """What PyGithub expects of a response (see github.Requester)."""

    def __init__(self, status: int, headers: dict[str, str], text: str) -> None:
        self.status = status
        self.headers = headers
        self.text = text

    def getheaders(self):
        return self.headers.items()

    def read(self) -> str:
        return self.text

    def iter_content(self, chunk_size: int | None = 1):
        data = self.text.encode()
        size = chunk_size or len(data) or 1
        return (data[i : i + size] for i in range(0, len(data), size))

    def raise_for_status(self) -> None:
        pass


def cached_connection(base: type, cache: ResponseCache) -> type:
    """A PyGithub connection class whose GET requests use the cache."""

    class CachedConnection(base):
        def getresponse(self):
            # The rate limit must always be fresh.
            if self.verb.upper() != "GET" or self.stream or "/rate_limit" in self.url:
                return super().getresponse()
            key = cache.key(
                self.headers.get("Authorization", ""),
                f"{self.host}:{self.port}{self.url}",
            )
            entry = cache.load(key)
            if entry:
                self.headers = {**self.headers, "If-None-Match": entry["etag"]}
            response = super().getresponse()
            if response.status == 304 and entry:
                cache.count(cached=True)
                # GitHub repeats Link and the rate limit headers on a 304: these
                # describe the current state (new pages, API calls used), not the
                # cached body.
                fresh = {
                    k.lower(): v
                    for k, v in response.getheaders()
                    if k.lower() not in ("content-length", "content-type")
                }
                return CachedResponse(200, {**entry["headers"], **fresh}, entry["body"])
            cache.count(cached=False)
            etag = response.headers.get("etag")
            if response.status == 200 and etag:
                headers = {
                    k.lower(): v
                    for k, v in response.getheaders()
                    if k.lower() != "set-cookie"
                }
                cache.store(
                    key, {"etag": etag, "headers": headers, "body": response.read()}
                )
            return response

    return CachedConnection


@contextmanager
def installed(cache: ResponseCache | None) -> Iterator[ResponseCache | None]:
    """Send all PyGithub requests through the cache inside this block.

    Injecting the connection classes makes PyGithub open a connection per
    request instead of sharing one, which is needed to send requests in
    parallel. Without a cache the requests are just not cached.
    """
    http, https = HTTPRequestsConnectionClass, HTTPSRequestsConnectionClass
    if cache:
        http, https = cached_connection(http, cache), cached_connection(https, cache)
    Requester.injectConnectionClasses(http, https)
    try:
        yield cache
    finally:
        Requester.resetConnectionClasses()
