"""Collecting and formatting contributor statistics."""

import re
import threading
from collections import defaultdict
from collections.abc import Callable, Iterable, Iterator
from concurrent.futures import Executor, ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime

from github import Auth, Github

from .cache import ResponseCache, installed

# (key in the rows, header of the table)
COLUMNS = (
    ("handle", "handle"),
    ("commits", "commits"),
    ("prs", "prs"),
    ("opened", "issues opened"),
    ("commented", "issues commented on"),
    ("pr_commented", "PRs commented on"),
    ("reviewed", "PRs reviewed"),
    ("activity", "last activity"),
)
SORT_KEYS = tuple(key for key, _ in COLUMNS)

REVIEW_PROGRESS_EVERY = 25
# PyGithub waits 0.25s between requests by default: too slow for the many
# requests of an analysis, which are sent one after the other.
READ_ATTEMPTS = 3  # to read a list that keeps changing
REQUEST_DELAY = 0.05
JOBS = 4  # requests at the same time, GitHub asks not to send too many
TEXT_WIDTH = 56  # of the progress messages, before the status
PER_PAGE = 100  # the maximum, so that the fewest API calls are needed


def reset_time(gh: Github) -> str:
    """When the rate limit window ends."""
    return datetime.fromtimestamp(gh.rate_limiting_resettime).strftime("%H:%M")


def latest(*dates: datetime | None) -> datetime | None:
    """The most recent of the dates that are known."""
    known = [d for d in dates if d is not None]
    return max(known) if known else None


def parse_date(text: str | None) -> datetime | None:
    return datetime.fromisoformat(text) if text else None


def last_page(link: str | None) -> int | None:
    """The number of the last page from a Link header."""
    match = re.search(r'[?&]page=(\d+)[^>]*>;\s*rel="last"', link or "")
    return int(match.group(1)) if match else None


class Collector:
    """Reads the repositories through PyGithub and counts per contributor.

    The requests that do not depend on each other, the pages of a list and the
    requests per pull request or contributor, are sent in parallel by the pool.
    The results are read in order by the main thread, which also reports the
    progress and does the counting.
    """

    def __init__(
        self,
        gh: Github,
        progress: Callable[[str], None],
        pool: Executor,
        cache: ResponseCache | None = None,
        token: str = "",
    ) -> None:
        self.gh = gh
        self.progress = progress
        self.pool = pool
        self.lock = threading.Lock()
        self.requests = 0  # sent so far
        self.active = 0  # being sent now
        self.peak = 0  # most at the same time since the step started
        self.window = None  # of the rate limit: when it resets
        self.lowest = None  # remaining API calls, the lowest seen in the window
        self.limit = None
        self.cache = cache
        self.token = token
        self.skipped = 0  # requests that were not needed since nothing changed
        self.rows: dict[str, dict] = defaultdict(
            lambda: {
                "handle": "",
                "commits": 0,
                "prs": 0,
                "merged": 0,
                "opened": 0,
                "commented": 0,
                "pr_commented": 0,
                "reviewed": 0,
                "activity": None,
            }
        )

    def status(self) -> str:
        """The requests answered by the cache and the API calls used.

        The numbers have a fixed width, so that the lines align."""
        limit = self.limit or self.gh.rate_limiting[1]
        parts = [f"API {self.used():>4}/{limit}"]
        if self.cache:
            parts.insert(0, f"cached {self.cache.stats.cached:>5}")
        return " | ".join(parts)

    def say(self, text: str, *more: str) -> None:
        self.progress(" | ".join([f"{text:<{TEXT_WIDTH}}", self.status(), *more]))

    def row(self, login: str, date: datetime | None = None) -> dict:
        row = self.rows[login]
        row["handle"] = login
        row["activity"] = latest(row["activity"], date)
        return row

    def get(self, path: str, page: int | None = None, **params) -> tuple[dict, list]:
        """One response: the headers and the JSON."""
        if page:
            params |= {"per_page": PER_PAGE, "page": page}
        with self.lock:
            self.requests += 1
            self.active += 1
            self.peak = max(self.peak, self.active)
        try:
            headers, data = self.gh.requester.requestJsonAndCheck(
                "GET", path, parameters=params
            )
            self.note_rate_limit(headers)
            return headers, data
        finally:
            with self.lock:
                self.active -= 1

    def note_rate_limit(self, headers: dict) -> None:
        """Keep the lowest remaining count of the window.

        Parallel responses can arrive in another order than they were
        answered, so the last one is not always the one with the fewest left."""
        try:
            remaining = int(headers["x-ratelimit-remaining"])
            limit = int(headers["x-ratelimit-limit"])
            window = headers.get("x-ratelimit-reset")
        except (KeyError, ValueError):
            return
        with self.lock:
            if window != self.window or self.lowest is None:
                self.window, self.lowest = window, remaining
            else:
                self.lowest = min(self.lowest, remaining)
            self.limit = limit

    def used(self) -> int:
        if self.lowest is None:
            remaining, limit = self.gh.rate_limiting
            return limit - remaining
        return self.limit - self.lowest

    @contextmanager
    def step(self, label: str) -> Iterator[None]:
        """Report after a step how its requests used the API calls."""
        requests, used = self.requests, self.used()
        cached = self.cache.stats.cached if self.cache else 0
        skipped = self.skipped
        self.peak = 0
        yield
        sent = self.requests - requests
        hits = (self.cache.stats.cached if self.cache else 0) - cached
        parallel = f"{self.peak} at once" if self.peak > 1 else "one at a time"
        parts = [f"{sent} request{'' if sent == 1 else 's'} ({parallel})"]
        if self.cache:
            parts.append(f"{hits} cached, {sent - hits} fetched")
            parts.append(f"{self.skipped - skipped} unchanged, not requested")
        parts.append(f"API +{self.used() - used}")
        self.progress(f"    {label}: {', '.join(parts)}")

    def fetch_pages(
        self, prefix: str, label: str, path: str, params: dict
    ) -> list[list[dict]]:
        """The pages of a list endpoint.

        The first page tells how many there are, then the others are requested
        in parallel. Pages that appeared in the meantime are read after them."""
        headers, items = self.get(path, 1, **params)
        link = headers.get("link", "")
        total = last_page(link) or 1
        self.say(f"{prefix}: {label} page 1/{total}")
        pages = [items]
        if total > 1:
            others = self.pool.map(
                lambda n: self.get(path, n, **params), range(2, total + 1)
            )
            for page, (headers, items) in enumerate(others, 2):
                self.say(f"{prefix}: {label} page {page}/{total}")
                pages.append(items)
                link = headers.get("link", "")
        while 'rel="next"' in link:  # new activity added pages
            headers, items = self.get(path, len(pages) + 1, **params)
            self.say(f"{prefix}: {label} page {len(pages) + 1}/{len(pages) + 1}")
            pages.append(items)
            link = headers.get("link", "")
        return pages

    def read_list(self, prefix: str, label: str, path: str, **params) -> list[dict]:
        """All items of a list endpoint, read again if it changed meanwhile.

        New activity moves items between the pages while they are read, so
        items could be in two pages or in none. The first and the last page are
        requested again; they are the same, and free if cached, unless the list
        changed. The caller still has to count each item only once."""
        for _ in range(READ_ATTEMPTS):
            pages = self.fetch_pages(prefix, label, path, params)
            first = self.get(path, 1, **params)[1]
            headers, last = self.get(path, len(pages), **params)
            unchanged = (
                first == pages[0]
                and last == pages[-1]
                and 'rel="next"' not in headers.get("link", "")
            )
            if unchanged:
                break
            self.say(f"{prefix}: {label} changed while reading, reading again")
        return [item for page in pages for item in page]

    def all(self, path: str, page: int = 1, **params) -> Iterator[dict]:
        """The items of a list endpoint from page on, without parallelism."""
        while True:
            headers, items = self.get(path, page, **params)
            yield from items
            if 'rel="next"' not in headers.get("link", ""):
                return
            page += 1

    def remembered(self, key: str, fetch: Callable[[], object]):
        """The value for key; fetch() is only called if it is not remembered.

        The key includes what changes when the value changes, so a remembered
        value is valid and no request is needed, not even to validate it."""
        if not self.cache:
            return fetch()
        key = self.cache.key(self.token, f"memo|{key}")
        value = self.cache.recall(key)
        if value is not None:
            with self.lock:
                self.skipped += 1
            return value
        value = fetch()
        self.cache.remember(key, value)
        return value

    def reviews(self, base: str, pull: dict) -> list[dict]:
        """The reviews as (login, state, date) of a pull request.

        Reviewing, commenting and merging change when the pull request was
        last updated."""

        def fetch():
            return [
                [
                    (r.get("user") or {}).get("login"),
                    r.get("state"),
                    r.get("submitted_at"),
                ]
                for r in self.all(f"{base}/pulls/{pull['number']}/reviews")
            ]

        if not pull.get("updated_at"):
            return fetch()
        return self.remembered(
            f"reviews|{base}|{pull['number']}|{pull['updated_at']}", fetch
        )

    def latest_commit(self, base: str, login: str, commits: int) -> list[str | None]:
        """The date of the newest commit of the contributor, as [date or None].

        It is the same while the contributor has the same number of commits."""

        def fetch():
            found = self.get(f"{base}/commits", author=login, per_page=1)[1]
            return [found[0]["commit"]["author"]["date"] if found else None]

        return self.remembered(f"latest|{base}|{login}|{commits}", fetch)

    def collect(self, number: int, count: int, name: str) -> None:
        """Read one repository and add it to the rows.

        What is read is first collected by number or login, so that an item
        which is seen twice, because the lists changed while they were read,
        updates the information instead of adding to it. The rows are only
        changed when everything is read."""
        prefix = f"[{number}/{count}] {name}"
        base = f"/repos/{name}"

        commits: dict[str, int] = {}
        with self.step("contributors"):
            items = self.read_list(prefix, "contributors", f"{base}/contributors")
        for item in items:
            if item.get("login"):
                commits[item["login"]] = item["contributions"]

        # The newest commit of each contributor: one small request each, which
        # is answered from the cache if the contributor has nothing new.
        logins = list(commits)
        activity: dict[str, datetime | None] = {}
        self.say(f"{prefix}: latest commits 0/{len(logins)}, one request each")
        with self.step("latest commits"):
            newest = self.pool.map(
                lambda login: self.latest_commit(base, login, commits[login]), logins
            )
            for position, (login, found) in enumerate(zip(logins, newest), 1):
                if found[0]:
                    activity[login] = parse_date(found[0])
                if position % PER_PAGE == 0 and position != len(logins):
                    self.say(f"{prefix}: latest commits {position}/{len(logins)}")
        self.say(f"{prefix}: latest commits {len(logins)}/{len(logins)}")

        # Oldest first: the pages of older items do not change when something
        # new is added, so they stay valid in the cache.
        oldest_first = {"sort": "created", "direction": "asc"}
        with self.step("pull requests"):
            all_pulls = self.read_list(
                prefix, "pull requests", f"{base}/pulls", state="all", **oldest_first
            )
        pulls = {pull["number"]: pull for pull in all_pulls}
        with self.step("issues"):
            all_issues = self.read_list(
                prefix, "issues", f"{base}/issues", state="all", **oldest_first
            )
        # the issues endpoint lists pull requests, too
        issues = {i["number"]: i for i in all_issues if "pull_request" not in i}

        def author(item: dict) -> str | None:
            return (item.get("user") or {}).get("login")

        pull_authors = {n: author(pull) for n, pull in pulls.items()}
        commented: dict[str, set[int]] = defaultdict(set)
        pr_commented: dict[str, set[int]] = defaultdict(set)
        reviewed: dict[str, set[int]] = defaultdict(set)

        def touch(login: str, date: datetime | None) -> None:
            activity[login] = latest(activity.get(login), date)

        for pull in pulls.values():
            if author(pull):
                touch(author(pull), parse_date(pull["created_at"]))
        for issue in issues.values():
            if author(issue):
                touch(author(issue), parse_date(issue["created_at"]))

        with self.step("comments"):
            comments = self.read_list(
                prefix, "comments", f"{base}/issues/comments", **oldest_first
            )
        for comment in comments:
            login = author(comment)
            if not login:
                continue
            number_ = int(comment["issue_url"].rsplit("/", 1)[1])
            if number_ in issues:
                commented[login].add(number_)
            elif number_ in pulls:
                if pull_authors[number_] != login:
                    pr_commented[login].add(number_)
            else:
                continue
            touch(login, parse_date(comment["created_at"]))

        # Comments on the changes of a pull request
        with self.step("review comments"):
            review_comments = self.read_list(
                prefix, "review comments", f"{base}/pulls/comments", **oldest_first
            )
        for comment in review_comments:
            login = author(comment)
            if not login:
                continue
            number_ = int(comment["pull_request_url"].rsplit("/", 1)[1])
            touch(login, parse_date(comment["created_at"]))
            if pull_authors.get(number_) != login:
                pr_commented[login].add(number_)

        # Everything else people did to issues and pull requests (closing,
        # merging, labelling, assigning, ...) and comments on commits. These
        # are no counts, but they are activity.
        with self.step("issue events"):
            events = self.read_list(prefix, "issue events", f"{base}/issues/events")
        for event in events:
            login = (event.get("actor") or {}).get("login")
            if login:
                touch(login, parse_date(event["created_at"]))
        with self.step("commit comments"):
            commit_comments = self.read_list(
                prefix, "commit comments", f"{base}/comments"
            )
        for comment in commit_comments:
            if author(comment):
                touch(author(comment), parse_date(comment["created_at"]))

        # The reviews can only be read per pull request: one request each,
        # which is answered from the cache if the pull request has nothing new.
        numbers = list(pulls)
        self.say(
            f"{prefix}: reviews of pull request 0/{len(numbers)}, one request each"
        )
        with self.step("reviews"):
            found = self.pool.map(lambda n: self.reviews(base, pulls[n]), numbers)
            for position, (number_, reviews) in enumerate(zip(numbers, found), 1):
                for login, state, submitted in reviews:
                    if not login or state == "PENDING":
                        continue
                    touch(login, parse_date(submitted))
                    if pull_authors[number_] != login:
                        reviewed[login].add(number_)
                if position % REVIEW_PROGRESS_EVERY == 0 and position != len(numbers):
                    self.say(
                        f"{prefix}: reviews of pull request {position}/{len(numbers)}"
                    )
        self.say(f"{prefix}: reviews of pull request {len(numbers)}/{len(numbers)}")

        # Everything is read: add it to the rows.
        for login, contributions in commits.items():
            self.row(login)["commits"] += contributions
        for pull in pulls.values():
            if author(pull):
                row = self.row(author(pull))
                row["prs"] += 1
                row["merged"] += pull["merged_at"] is not None
        for issue in issues.values():
            if author(issue):
                self.row(author(issue))["opened"] += 1
        for key, found_in in (
            ("commented", commented),
            ("pr_commented", pr_commented),
            ("reviewed", reviewed),
        ):
            for login, numbers_ in found_in.items():
                self.row(login)[key] += len(numbers_)
        for login, date in activity.items():
            self.row(login, date)

    def result(self) -> list[dict]:
        return list(self.rows.values())


def collect(
    token: str,
    repositories: Iterable[str],
    progress: Callable[[str], None] = lambda message: None,
    cache: ResponseCache | None = None,
    base_url: str = "https://api.github.com",
    jobs: int = JOBS,
) -> list[dict]:
    """Return one row per contributor, summed over all repositories.

    All requests go through cache if given: what did not change since the last
    analysis is answered by a conditional request that uses no API calls.
    Up to jobs requests are sent at the same time.
    progress is called with a status message after every page of results; it
    shows the requests answered by the cache and the API calls used.
    """
    repositories = list(repositories)
    with installed(cache), ThreadPoolExecutor(max_workers=jobs) as pool:
        gh = Github(
            auth=Auth.Token(token),
            per_page=PER_PAGE,
            base_url=base_url,
            seconds_between_requests=REQUEST_DELAY,
        )
        collector = Collector(gh, progress, pool, cache, token)
        for number, name in enumerate(repositories, 1):
            collector.collect(number, len(repositories), name)
        rows = collector.result()
        collector.say(
            f"Done: {len(rows)} contributors in {len(repositories)} repositories",
            f"resets {reset_time(gh)}",
        )
        return rows


def sort_rows(rows: list[dict], column: str = "prs") -> list[dict]:
    """Sort by a column key: handles ascending, the rest highest/newest first.

    The prs column is merged/total, but it sorts by merged only. Ties are
    sorted by handle.
    """
    if column == "handle":
        return sorted(rows, key=lambda r: r["handle"].lower())
    if column == "activity":
        epoch = datetime.min.replace(tzinfo=UTC)
        return sorted(
            rows,
            key=lambda r: (-(r["activity"] or epoch).timestamp(), r["handle"].lower()),
        )
    key = "merged" if column == "prs" else column
    return sorted(rows, key=lambda r: (-r[key], r["handle"].lower()))


def days_ago(date: datetime | None, now: datetime) -> str:
    """How long ago the date is, in days; "-" if there is no activity."""
    if date is None:
        return "-"
    days = max((now - date).days, 0)
    if days == 0:
        return "today"
    return "1 day ago" if days == 1 else f"{days} days ago"


def to_markdown(rows: list[dict], now: datetime | None = None) -> str:
    """Render rows as a padded Markdown table; numbers are right-aligned.

    The prs column shows merged/total. The last activity column shows how many
    days ago the newest activity in the repositories was: any of the data that
    is read, such as a commit, pull request, issue, comment, review or an issue
    event like closing or merging.
    """
    now = now or datetime.now(UTC)
    headers = [header for _, header in COLUMNS]
    cells = [
        [
            r["handle"],
            str(r["commits"]),
            f"{r['merged']}/{r['prs']}",
            str(r["opened"]),
            str(r["commented"]),
            str(r["pr_commented"]),
            str(r["reviewed"]),
            days_ago(r["activity"], now),
        ]
        for r in rows
    ]
    widths = [
        max(len(h), *(len(row[i]) for row in cells)) for i, h in enumerate(headers)
    ]

    def line(values: list[str]) -> str:
        parts = [
            v.ljust(w) if i == 0 else v.rjust(w)
            for i, (v, w) in enumerate(zip(values, widths, strict=True))
        ]
        return "| " + " | ".join(parts) + " |"

    sep = (
        "| "
        + " | ".join(
            "-" * w if i == 0 else "-" * (w - 1) + ":" for i, w in enumerate(widths)
        )
        + " |"
    )
    return "\n".join([line(headers), sep, *(line(r) for r in cells)])
