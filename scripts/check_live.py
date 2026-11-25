"""Check a running site from outside, as a visitor who is not signed in.

Usage: ``make check-live``, or ``LIVE_URL=https://community.example.org make check-live``.
``LIVE_COMMIT`` (the CI sets the commit it pushed) makes the check wait for that version.

The check

1. waits while the site starts or is updated, up to ``LIVE_WAIT`` seconds: until ``/health/``
   answers 200 and, with ``LIVE_COMMIT``, ``/about/`` names that commit, so that the old
   container, which answers until the new one runs, does not pass the check;
2. opens the public pages and follows their links to other public pages;
3. takes the first public repository of Explore and opens its pages, a chart and its badge;
   only one, as each statistic is computed on request;
4. checks that robots.txt keeps crawlers away from the statistics;
5. checks that errors get the pages of the site: a missing page is 404, not 500, and the
   pages of signed in people ask to sign in.

It only reads.
"""

import os
import re
import sys
import time
import uuid
from collections import deque
from urllib.parse import urljoin, urlsplit

import httpx

DEFAULT_URL = "https://insight.pycal.org"
# the pages for everybody that the walk follows; the statistics are opened for one scope only
PUBLIC = re.compile(r"^/(|explore/|about/|health/|robots\.txt|favicon\.ico|accounts/login/)$")
SIGN_IN = "/accounts/login/"
START = ["/", "/explore/", "/about/", "/health/", "/robots.txt", "/favicon.ico", SIGN_IN]
# the pages of a public scope, after /s/<scope>/
SCOPE_PAGES = [
    "",
    "trends/?last=30",
    "response-times/",
    "contributors/",
    "countries/",
    "languages/",
    "items/",
    "replies/",
    "reviews/",
    "suggestions/",
    "badges/",
    "chart/trend-pr.svg?last=30",
]
SCOPE = re.compile(r'href="/s/([^"/?]+)/"')
# what the pages of the site have, and the error pages of nginx do not
SITE_PAGE = "data-theme-choice"
TRIES = 3  # tries of a request that gets no answer, such as a timeout, or that of a busy site
# what nginx answers while gunicorn is busy, such as with the first statistics after a deploy
BUSY = (502, 503, 504)
RETRY_PAUSE = 10


class LiveCheck:
    """Open the public pages of a site and check its error pages."""

    def __init__(
        self,
        url: str,
        client: httpx.Client | None = None,
        wait: float = 600,
        commit: str = "",
    ):
        """The check of the site at *url*.

        Args:
            url: The address of the site, such as ``https://insight.pycal.org``.
            client: The HTTP client; one without redirects by default.
            wait: How long to wait for the site to start, in seconds.
            commit: The commit the site must run, "" for any.
        """
        self.url = url.rstrip("/")
        # statistics of a large repository take a while when nothing is cached
        self.client = client or httpx.Client(timeout=120, follow_redirects=False)
        self.wait = wait
        self.commit = commit
        self.failures: list[str] = []
        self.checked: dict[str, int] = {}

    def report(self, ok: bool, status: int | str, path: str, note: str = "") -> None:
        """Print one result and keep the failures.

        Args:
            ok: Whether the result is as expected.
            status: The HTTP status, or what happened.
            path: The page.
            note: What was expected, for failures.
        """
        line = f"{'ok  ' if ok else 'FAIL'} {status} {path}" + (f"  ({note})" if note else "")
        print(line, flush=True)
        if not ok:
            self.failures.append(line)

    def get(self, path: str) -> httpx.Response:
        """GET a page of the site, without following redirects.

        Args:
            path: The path, such as ``/about/``.

        Returns:
            The answer; one with the status 599 and the reason if there was none after
            ``TRIES`` tries, such as after timeouts while the site is busy after a restart. A
            busy answer (``BUSY``, such as 502 when the first statistics after a deploy take
            longer than gunicorn waits) is tried again, too, and returned after the last try.
        """
        address = urljoin(self.url + "/", path.lstrip("/"))
        answer = None
        for attempt in range(TRIES):
            try:
                answer = self.client.get(address)
                if answer.status_code not in BUSY:
                    return answer
                reason = f"busy: {answer.status_code}"
            except httpx.TransportError as error:
                answer = None
                reason = f"{type(error).__name__}: {error}"
            print(f"retry {path}: {reason}", flush=True)
            if attempt + 1 < TRIES:
                time.sleep(RETRY_PAUSE)
        return answer if answer is not None else httpx.Response(599, text=reason)

    def running(self) -> str:
        """What keeps the check waiting, "" when the site runs the version wanted.

        Returns:
            Why it waits, such as ``/health/ 502``.
        """
        status = self.get("/health/").status_code
        if status != 200:
            return f"/health/ {status}"
        if self.commit and self.commit not in self.get("/about/").text:
            return f"/about/ does not name the commit {self.commit[:12]} yet"
        return ""

    def wait_until_up(self, pause: float = 10) -> bool:
        """Wait while the site starts, and until it runs the commit wanted.

        Args:
            pause: Seconds between the tries.

        Returns:
            True when it is up within the time.
        """
        end = time.monotonic() + self.wait
        while True:
            reason = self.running()
            if not reason:
                note = f"up with {self.commit}" if self.commit else "up"
                self.report(True, 200, "/health/", note)
                return True
            if time.monotonic() >= end:
                self.report(False, reason, "/health/", f"not up in {self.wait:g} s")
                return False
            print(f"wait: {reason}", flush=True)
            time.sleep(pause)

    @staticmethod
    def links(html: str) -> list[str]:
        """The paths of the links of a page to pages of the same site.

        Args:
            html: The page.

        Returns:
            The paths, without queries and fragments, each once, in their order.

        Examples:
            >>> LiveCheck.links('<a href="/about/">a</a> <a href="https://x.org/">b</a>'
            ...                 '<a href="/explore/#top">c</a> <a href="/about/?next=/">d</a>')
            ['/about/', '/explore/']
        """
        found = []
        for href in re.findall(r'href="([^"]+)"', html):
            parts = urlsplit(href.replace("&amp;", "&"))
            if parts.scheme or parts.netloc or not parts.path.startswith("/"):
                continue
            if parts.path not in found:
                found.append(parts.path)
        return found

    def check_page(self, path: str) -> str | None:
        """Open a public page: it must open without signing in, without an error.

        Args:
            path: The page, with its parameters.

        Returns:
            The text of the page, or None if it failed or redirected.
        """
        response = self.get(path)
        self.checked[path] = response.status_code
        location = response.headers.get("location", "")
        if response.status_code == 200:
            if "Traceback" in response.text or "Server Error" in response.text:
                self.report(False, 200, path, "the page shows a server error")
                return None
            self.report(True, 200, path)
            return response.text
        if response.status_code in (301, 302) and SIGN_IN in location:
            self.report(False, response.status_code, path, "public, but asks to sign in")
        elif response.status_code in (301, 302, 307, 308):
            target = urlsplit(urljoin(self.url + path, location))
            same = f"{target.scheme}://{target.netloc}" == self.url
            self.report(same, response.status_code, path, "" if same else f"leaves to {location}")
        else:
            self.report(False, response.status_code, path, "expected 200")
        return None

    def walk(self) -> str:
        """Open the public pages and follow their links to other public pages.

        Returns:
            The page Explore, "" if it did not open.
        """
        queue = deque(START)
        seen = set(START)
        explore = ""
        while queue:
            path = queue.popleft()
            text = self.check_page(path) or ""
            if path == "/explore/":
                explore = text
            for link in self.links(text):
                if link not in seen and PUBLIC.match(link):
                    seen.add(link)
                    queue.append(link)
        return explore

    def check_scope(self, explore: str) -> None:
        """Open the pages of the first public repository of Explore, a chart and its badge.

        Args:
            explore: The page Explore.
        """
        found = SCOPE.search(explore)
        if not found:
            self.report(False, "-", "/explore/", "no public repository to open")
            return
        scope = found.group(1)
        print(f"scope /s/{scope}/", flush=True)
        for page in SCOPE_PAGES:
            self.check_page(f"/s/{scope}/{page}")
        self.check_page(f"/badge/s/{scope}.svg")

    def check_robots(self) -> None:
        """robots.txt keeps crawlers away from the statistics."""
        response = self.get("/robots.txt")
        kept = response.status_code == 200 and "Disallow: /s/" in response.text
        note = "" if kept else "expected Disallow: /s/"
        self.report(kept, response.status_code, "/robots.txt (rules)", note)

    def expect(self, path: str, status: int) -> None:
        """Check the answer of a page that is not public or does not exist.

        Args:
            path: The page.
            status: The status that is right: 302 must ask to sign in, 404 must be the
                page of the site, not of nginx.
        """
        response = self.get(path)
        ok = response.status_code == status
        note = f"expected {status}"
        if ok and status == 302:
            # the admin sends to its own sign in first, which asks to sign in on the site
            location = response.headers.get("location", "")
            ok = SIGN_IN in location or location.startswith("/admin/login/")
            note = "expected to ask to sign in"
        elif ok and status == 404:
            ok = SITE_PAGE in response.text
            note = "expected the error page of the site"
        self.report(ok, response.status_code, path, "" if ok else note)

    def check_errors(self) -> None:
        """Errors get the pages of the site; the pages of signed in people ask to sign in."""
        unknown = uuid.uuid4().hex[:12]
        self.expect(f"/no-page-{unknown}/x/y/", 404)
        self.expect(f"/s/nobody-{unknown}~nothing/", 404)
        self.expect("/about/licenses/no-such-license/", 404)
        for path in ("/dashboard/", "/dashboard/github/", "/s/1/", "/messages/", "/admin/"):
            self.expect(path, 302)

    def run(self) -> int:
        """Check the site.

        Returns:
            The exit code: 0 if everything is right.
        """
        print(f"Checking {self.url}", flush=True)
        if not self.wait_until_up():
            return 1
        self.check_scope(self.walk())
        self.check_robots()
        self.check_errors()
        print(f"{len(self.checked)} public pages, {len(self.failures)} failures", flush=True)
        for line in self.failures:
            print(line, flush=True)
        return 1 if self.failures else 0


if __name__ == "__main__":
    check = LiveCheck(
        os.environ.get("LIVE_URL") or DEFAULT_URL,
        wait=float(os.environ.get("LIVE_WAIT", 600)),
        commit=os.environ.get("LIVE_COMMIT", ""),
    )
    sys.exit(check.run())
