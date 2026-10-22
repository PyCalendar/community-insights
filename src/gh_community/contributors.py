"""Collecting and formatting contributor statistics."""

import difflib
import re
import threading
from collections import defaultdict
from collections.abc import Callable, Iterable, Iterator
from concurrent.futures import Executor, ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime
from statistics import median

from github import Auth, Github

from .cache import ResponseCache, installed


def _count(key: str, header: str):
    """A column with the number in the row key."""
    return (header, lambda r, now: str(r[key]), False)


def _part(part: Callable[[dict], int], total: str, header: str):
    """A column with a part of the total in the row key, as X/total."""
    return (header, lambda r, now: f"{part(r)}/{r[total]}", False)


# The columns of the table that can be chosen: name -> (header, text, left aligned)
# where text(row, now) is the content of a cell. The names are the ones of the
# variables of the expressions (and of the columns of the CSV), grouped by prefix:
# user_, commits_, prs_, issues_, comments_, actions_, days_, months_. Parts of
# the pull requests or issues opened are shown as X/total.
COLUMN_DEFS: dict[str, tuple[str, Callable[[dict, datetime], str], bool]] = {
    "user_handle": ("handle", lambda r, now: r["user_handle"], True),
    "user_association": (
        "association",
        lambda r, now: r["user_association"] or "-",
        True,
    ),
    "user_bot": (
        "bot",
        lambda r, now: "yes" if is_bot(r["user_handle"]) else "no",
        True,
    ),
    "commits_total": _count("commits_total", "commits"),
    "prs_total": _count("prs_total", "PRs"),
    "prs_open": _part(lambda r: r["prs_open"], "prs_total", "open PRs"),
    "prs_merged": _part(lambda r: r["prs_merged"], "prs_total", "merged PRs"),
    "prs_unmerged": _part(lambda r: r["prs_unmerged"], "prs_total", "unmerged PRs"),
    "prs_closed": _part(
        lambda r: r["prs_merged"] + r["prs_unmerged"], "prs_total", "closed PRs"
    ),
    "prs_commented": _count("prs_commented", "PRs commented on"),
    "prs_reviewed": _count("prs_reviewed", "PRs reviewed"),
    "prs_approved": _count("prs_approved", "PRs approved"),
    "prs_changes_requested": _count("prs_changes_requested", "changes requested"),
    "issues_opened": _count("issues_opened", "issues opened"),
    "issues_open": _part(lambda r: r["issues_open"], "issues_opened", "open issues"),
    "issues_closed": _part(
        lambda r: r["issues_opened"] - r["issues_open"],
        "issues_opened",
        "closed issues",
    ),
    "issues_commented": _count("issues_commented", "issues commented on"),
    "comments_total": _count("comments_total", "comments"),
    "actions_merges": _count("actions_merges", "merges"),
    "actions_closes": _count("actions_closes", "closes"),
    "actions_labels": _count("actions_labels", "labels"),
    "days_first": (
        "first activity",
        lambda r, now: days_ago(r["date_first"], now),
        False,
    ),
    "days_last": ("last activity", lambda r, now: days_ago(r["date_last"], now), False),
    "days_to_merge": (
        "days to merge",
        lambda r, now: "-" if r["days_to_merge"] is None else f"{r['days_to_merge']:g}",
        False,
    ),
    "months_active": _count("months_active", "active months"),
}
DEFAULT_COLUMNS = (
    "user_handle",
    "commits_total",
    "prs_merged",
    "issues_opened",
    "issues_commented",
    "prs_commented",
    "prs_reviewed",
    "days_last",
)


def is_bot(handle: str) -> bool:
    """Bots have [bot] in their handle; Copilot has none."""
    handle = handle.lower()
    return "[bot]" in handle or handle in BOT_HANDLES


def unknown(kind: str, name: str, choices: Iterable[str]) -> str:
    """An error text for an unknown name, with the closest names and all of them."""
    choices = sorted(choices)
    close = difflib.get_close_matches(name.lower(), choices, n=2, cutoff=0.6)
    # also names that contain it or are part of it, for example "open" for prs_open
    close += [
        c for c in choices if name and (name in c or c in name) and c not in close
    ][: 3 - len(close)]
    hint = f" Did you mean {' or '.join(repr(c) for c in close)}?" if close else ""
    return f"Unknown {kind} {name!r}.{hint} Use one of: {', '.join(choices)}."


COLUMNS_SYNTAX = re.compile(r"[+-]?[a-z_]+([+-][a-z_]+)*")


def parse_columns(text: str, default: Iterable[str] = DEFAULT_COLUMNS) -> list[str]:
    """The columns of a specification, split by + and -; ValueError if invalid.

    A specification that starts with + or - changes the default columns: +x-y
    adds x and removes y. One that starts with a name is the list of columns:
    x+y shows x and y. Adding a column that is shown or removing one that is not
    changes nothing.
    """
    text = text.strip()
    if "," in text:
        raise ValueError("Separate the columns with + and -, not with a comma.")
    if not COLUMNS_SYNTAX.fullmatch(text):
        raise ValueError(
            f"{text!r} is not a column specification like +x-y or x+y, with the "
            "names of columns."
        )
    names = re.findall(r"[a-z_]+", text)
    for name in names:
        if name not in COLUMN_DEFS:
            raise ValueError(unknown("column", name, COLUMN_DEFS))
    columns = list(default) if text[0] in "+-" else []
    for sign, name in re.findall(r"([+-]?)([a-z_]+)", text):
        if sign == "-":
            columns = [c for c in columns if c != name]
        elif name not in columns:
            columns.append(name)
    if not columns:
        raise ValueError("No columns are left.")
    return columns


# bots whose handle does not contain [bot]
BOT_HANDLES = ("copilot",)

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


def earliest(*dates: datetime | None) -> datetime | None:
    """The oldest of the dates that are known."""
    known = [d for d in dates if d is not None]
    return min(known) if known else None


# GitHub's author_association, from the most privileged, in lowercase as stored
ASSOCIATIONS = (
    "owner",
    "member",
    "collaborator",
    "contributor",
    "first_timer",
    "first_time_contributor",
    "mannequin",
    "none",
)


def more_privileged(*names: str | None) -> str:
    """The most privileged of the association names; "" if none is known."""
    known = [n.lower() for n in names if n and n.lower() in ASSOCIATIONS]
    return min(known, key=ASSOCIATIONS.index) if known else ""


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
                "user_handle": "",
                "commits_total": 0,
                "prs_total": 0,
                "prs_open": 0,
                "prs_merged": 0,
                "prs_unmerged": 0,  # closed without being merged
                "issues_opened": 0,
                "issues_open": 0,
                "issues_commented": 0,
                "prs_commented": 0,
                "prs_reviewed": 0,
                "prs_approved": 0,
                "prs_changes_requested": 0,
                "comments_total": 0,  # all comments, not only the issues they are on
                "actions_merges": 0,  # pull requests merged by the user
                "actions_closes": 0,  # issues and pull requests closed, not by merging
                "actions_labels": 0,  # labels set
                "user_association": "",  # the most privileged one seen
                "date_first": None,
                "months_active": 0,
                "days_to_merge": None,  # median days until their pull requests merged
                "date_last": None,
                # collected, then reduced to months_active and days_to_merge
                "months": set(),
                "merge_times": [],
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

    def row(self, login: str, dates: Iterable[datetime] = ()) -> dict:
        row = self.rows[login]
        row["user_handle"] = login
        dates = list(dates)
        if dates:
            row["date_last"] = latest(row["date_last"], max(dates))
            row["date_first"] = earliest(row["date_first"], min(dates))
            row["months"] |= {d.strftime("%Y-%m") for d in dates}
        return row

    def get(self, path: str, page: int | None = None, **params) -> tuple[dict, list]:
        """One response: the headers and the JSON."""
        if page:
            params |= {"per_page": PER_PAGE, "page": page}
        return self.send("GET", path, parameters=params)

    def send(self, verb: str, path: str, **kwargs) -> tuple[dict, object]:
        """One request, counted: the headers and the JSON of the response."""
        with self.lock:
            self.requests += 1
            self.active += 1
            self.peak = max(self.peak, self.active)
        try:
            headers, data = self.gh.requester.requestJsonAndCheck(verb, path, **kwargs)
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
        dates: dict[str, list[datetime]] = defaultdict(list)
        self.say(f"{prefix}: latest commits 0/{len(logins)}, one request each")
        with self.step("latest commits"):
            newest = self.pool.map(
                lambda login: self.latest_commit(base, login, commits[login]), logins
            )
            for position, (login, found) in enumerate(zip(logins, newest), 1):
                if found[0]:
                    dates[login].append(parse_date(found[0]))
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
        approved: dict[str, set[int]] = defaultdict(set)
        changes_requested: dict[str, set[int]] = defaultdict(set)
        comment_counts: dict[str, int] = defaultdict(int)
        actions: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        def touch(login: str, date: datetime | None) -> None:
            if date:
                dates[login].append(date)

        associations: dict[str, str] = {}

        def associate(item: dict) -> None:
            """Remember the association of the author of an item."""
            if author(item):
                associations[author(item)] = more_privileged(
                    associations.get(author(item)), item.get("author_association")
                )

        for pull in pulls.values():
            associate(pull)
            if author(pull):
                touch(author(pull), parse_date(pull["created_at"]))
        for issue in issues.values():
            associate(issue)
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
                if author(issues[number_]) != login:
                    commented[login].add(number_)
            elif number_ in pulls:
                if pull_authors[number_] != login:
                    pr_commented[login].add(number_)
            else:
                continue
            comment_counts[login] += 1
            associate(comment)
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
            comment_counts[login] += 1
            associate(comment)
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
                number_ = (event.get("issue") or {}).get("number")
                kind = event.get("event")
                if kind == "closed":
                    # merging a pull request closes it, too: that is a merge
                    if not (pulls.get(number_) or {}).get("merged_at"):
                        actions[login]["actions_closes"] += 1
                elif kind == "merged":
                    actions[login]["actions_merges"] += 1
                elif kind == "labeled":
                    actions[login]["actions_labels"] += 1
        with self.step("commit comments"):
            commit_comments = self.read_list(
                prefix, "commit comments", f"{base}/comments"
            )
        for comment in commit_comments:
            if author(comment):
                comment_counts[author(comment)] += 1
                associate(comment)
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
                        if state == "APPROVED":
                            approved[login].add(number_)
                        elif state == "CHANGES_REQUESTED":
                            changes_requested[login].add(number_)
                if position % REVIEW_PROGRESS_EVERY == 0 and position != len(numbers):
                    self.say(
                        f"{prefix}: reviews of pull request {position}/{len(numbers)}"
                    )
        self.say(f"{prefix}: reviews of pull request {len(numbers)}/{len(numbers)}")

        # Everything is read: add it to the rows.
        for login, contributions in commits.items():
            self.row(login)["commits_total"] += contributions
        for pull in pulls.values():
            if author(pull):
                row = self.row(author(pull))
                row["prs_total"] += 1
                if pull["merged_at"] is not None:
                    row["prs_merged"] += 1
                    created, merged = pull["created_at"], pull["merged_at"]
                    row["merge_times"].append(
                        (parse_date(merged) - parse_date(created)).total_seconds()
                        / 86400
                    )
                elif pull["state"] == "open":
                    row["prs_open"] += 1
                else:
                    row["prs_unmerged"] += 1
        for issue in issues.values():
            if author(issue):
                row = self.row(author(issue))
                row["issues_opened"] += 1
                row["issues_open"] += issue.get("state") == "open"
        for key, found_in in (
            ("issues_commented", commented),
            ("prs_commented", pr_commented),
            ("prs_reviewed", reviewed),
            ("prs_approved", approved),
            ("prs_changes_requested", changes_requested),
        ):
            for login, numbers_ in found_in.items():
                self.row(login)[key] += len(numbers_)
        for login, counted in comment_counts.items():
            self.row(login)["comments_total"] += counted
        for login, done in actions.items():
            for key, counted in done.items():
                self.row(login)[key] += counted
        for login, association in associations.items():
            row = self.row(login)
            row["user_association"] = more_privileged(
                row["user_association"], association
            )
        for login, found_dates in dates.items():
            self.row(login, found_dates)

    def result(self) -> list[dict]:
        """The rows, with the collected months and times reduced to numbers."""
        for row in self.rows.values():
            row["months_active"] = len(row.pop("months"))
            times = row.pop("merge_times")
            row["days_to_merge"] = round(median(times), 1) if times else None
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


def days_ago(date: datetime | None, now: datetime) -> str:
    """How long ago the date is, in days (no "ago"); "-" if there is no activity."""
    if date is None:
        return "-"
    days = max((now - date).days, 0)
    if days == 0:
        return "today"
    # a space at the end, so that it lines up with "N days" in the plain text table
    return "1 day " if days == 1 else f"{days} days"


def to_markdown(
    rows: list[dict],
    now: datetime | None = None,
    columns: Iterable[str] = DEFAULT_COLUMNS,
) -> str:
    """Render rows as a padded Markdown table; numbers are right-aligned.

    The prs column shows merged/total. The last activity column shows how many
    days ago the newest activity in the repositories was: any of the data that
    is read, such as a commit, pull request, issue, comment, review or an issue
    event like closing or merging.
    """
    now = now or datetime.now(UTC)
    defs = [COLUMN_DEFS[c] for c in columns]
    headers = [header for header, _, _ in defs]
    cells = [[text(r, now) for _, text, _ in defs] for r in rows]
    left = [is_left for _, _, is_left in defs]
    widths = [
        max(len(h), *(len(row[i]) for row in cells)) for i, h in enumerate(headers)
    ]

    def line(values: list[str]) -> str:
        parts = [
            v.ljust(w) if left[i] else v.rjust(w)
            for i, (v, w) in enumerate(zip(values, widths, strict=True))
        ]
        return "| " + " | ".join(parts) + " |"

    sep = (
        "| "
        + " | ".join(
            "-" * w if left[i] else "-" * (w - 1) + ":" for i, w in enumerate(widths)
        )
        + " |"
    )
    return "\n".join([line(headers), sep, *(line(r) for r in cells)])
