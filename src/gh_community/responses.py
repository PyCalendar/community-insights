"""How long pull requests and issues wait for their first response."""

import math
from collections import defaultdict
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from statistics import mean, median

from github import Auth, Github

from .cache import ResponseCache, installed
from .contributors import (
    JOBS,
    PER_PAGE,
    REQUEST_DELAY,
    REVIEW_PROGRESS_EVERY,
    Collector,
    is_bot,
    parse_date,
)

# Who gave the first response, in the order of the chart.
BOT = "bot"
EXTERNAL = "external"
COLLABORATOR = "collaborator or higher"
CLASSES = (BOT, EXTERNAL, COLLABORATOR)

# the associations that are part of the project
MEMBERS = ("owner", "member", "collaborator")

# The upper limit of each column of the chart: label, time.
BUCKETS: list[tuple[str, timedelta]] = [
    ("1h", timedelta(hours=1)),
    ("3h", timedelta(hours=3)),
    ("6h", timedelta(hours=6)),
    ("12h", timedelta(hours=12)),
    ("24h", timedelta(hours=24)),
    ("2d", timedelta(days=2)),
    ("3d", timedelta(days=3)),
    ("5d", timedelta(days=5)),
    ("1w", timedelta(weeks=1)),
    ("2w", timedelta(weeks=2)),
    ("3w", timedelta(weeks=3)),
]
SLOWER = "more"  # the label of what takes longer than the last column
MAX_BAR = 40  # characters of the longest bar; longer ones are scaled down


def classify(login: str, association: str | None, bot: bool = False) -> str:
    """Whether a response is by a bot, an external person or a collaborator."""
    if bot or is_bot(login):
        return BOT
    return COLLABORATOR if (association or "").lower() in MEMBERS else EXTERNAL


class ResponseCollector(Collector):
    """Reads when the pull requests and issues were first answered."""

    def review_responses(self, base: str, pull: dict) -> list[list]:
        """The reviews as [login, association, bot, date] of a pull request.

        Remembered while the pull request was not updated, like the reviews of
        the contributors analysis."""

        def fetch():
            return [
                [
                    (r.get("user") or {}).get("login"),
                    r.get("author_association"),
                    (r.get("user") or {}).get("type") == "Bot",
                    r.get("submitted_at"),
                ]
                for r in self.all(f"{base}/pulls/{pull['number']}/reviews")
                if r.get("state") != "PENDING"
            ]

        if not pull.get("updated_at"):
            return fetch()
        return self.remembered(
            f"review responses|{base}|{pull['number']}|{pull['updated_at']}", fetch
        )

    def collect_responses(
        self, number: int, count: int, name: str
    ) -> dict[str, list[tuple[str, timedelta] | None]]:
        """Read one repository: per kind ("prs", "issues") one entry for each
        item, the class and time of the first response or None if there is none.
        """
        prefix = f"[{number}/{count}] {name}"
        base = f"/repos/{name}"
        oldest_first = {"sort": "created", "direction": "asc"}

        with self.step("pull requests"):
            pulls = self.read_list(
                prefix, "pull requests", f"{base}/pulls", state="all", **oldest_first
            )
        with self.step("issues"):
            all_issues = self.read_list(
                prefix, "issues", f"{base}/issues", state="all", **oldest_first
            )
        pulls = {p["number"]: p for p in pulls}
        issues = {i["number"]: i for i in all_issues if "pull_request" not in i}
        with self.step("comments"):
            comments = self.read_list(
                prefix, "comments", f"{base}/issues/comments", **oldest_first
            )
        with self.step("review comments"):
            review_comments = self.read_list(
                prefix, "review comments", f"{base}/pulls/comments", **oldest_first
            )

        # (date, class) of every response from someone else than the author
        responses: dict[tuple[str, int], list[tuple[datetime, str]]] = defaultdict(list)

        def author(item: dict) -> str | None:
            return (item.get("user") or {}).get("login")

        def respond(kind: str, number_: int, owner: dict, login, date, response):
            """Add a response, unless it is by the author or of an unknown item."""
            if login and login != author(owner) and date:
                responses[kind, number_].append((parse_date(date), response))

        def comment_class(comment: dict) -> str:
            user = comment.get("user") or {}
            return classify(
                user.get("login", ""),
                comment.get("author_association"),
                user.get("type") == "Bot",
            )

        for comment in comments:
            number_ = int(comment["issue_url"].rsplit("/", 1)[1])
            for kind, items in (("issues", issues), ("prs", pulls)):
                if number_ in items:
                    respond(
                        kind, number_, items[number_], author(comment),
                        comment["created_at"], comment_class(comment),
                    )  # fmt: skip
        for comment in review_comments:
            number_ = int(comment["pull_request_url"].rsplit("/", 1)[1])
            if number_ in pulls:
                respond(
                    "prs", number_, pulls[number_], author(comment),
                    comment["created_at"], comment_class(comment),
                )  # fmt: skip

        numbers = list(pulls)
        self.say(
            f"{prefix}: reviews of pull request 0/{len(numbers)}, one request each"
        )
        with self.step("reviews"):
            found = self.pool.map(
                lambda n: self.review_responses(base, pulls[n]), numbers
            )
            for position, (number_, reviews) in enumerate(zip(numbers, found), 1):
                for login, association, bot, date in reviews:
                    respond(
                        "prs", number_, pulls[number_], login, date,
                        classify(login or "", association, bot),
                    )  # fmt: skip
                if position % REVIEW_PROGRESS_EVERY == 0 and position != len(numbers):
                    self.say(
                        f"{prefix}: reviews of pull request {position}/{len(numbers)}"
                    )
        self.say(f"{prefix}: reviews of pull request {len(numbers)}/{len(numbers)}")

        result: dict[str, list[tuple[str, timedelta] | None]] = {
            "prs": [],
            "issues": [],
        }
        for kind, items in (("prs", pulls), ("issues", issues)):
            for number_, item in items.items():
                created = parse_date(item["created_at"])
                found_responses = responses.get((kind, number_))
                if not found_responses:
                    result[kind].append(None)
                    continue
                date, response = min(found_responses)
                result[kind].append((response, max(date - created, timedelta())))
        return result


def collect_responses(
    token: str,
    repositories: Iterable[str],
    progress: Callable[[str], None] = lambda message: None,
    cache: ResponseCache | None = None,
    base_url: str = "https://api.github.com",
    jobs: int = JOBS,
) -> dict[str, list[tuple[str, timedelta] | None]]:
    """The first responses of the pull requests ("prs") and issues ("issues").

    One entry per pull request or issue: the class of the first response (bot,
    external, collaborator or higher) and the time it took, or None if nobody
    but the author responded. The cache and the parallel requests are the
    same as for collect().
    """
    repositories = list(repositories)
    result: dict[str, list[tuple[str, timedelta] | None]] = {"prs": [], "issues": []}
    with installed(cache), ThreadPoolExecutor(max_workers=jobs) as pool:
        gh = Github(
            auth=Auth.Token(token),
            per_page=PER_PAGE,
            base_url=base_url,
            seconds_between_requests=REQUEST_DELAY,
        )
        collector = ResponseCollector(gh, progress, pool, cache, token)
        for number, name in enumerate(repositories, 1):
            for kind, entries in collector.collect_responses(
                number, len(repositories), name
            ).items():
                result[kind] += entries
        collector.say(f"Done: {len(repositories)} repositories")
    return result


def bucket(delay: timedelta) -> str:
    """The label of the column of the chart a response time is counted in."""
    return next((label for label, limit in BUCKETS if delay <= limit), SLOWER)


def histogram(
    entries: list[tuple[str, timedelta] | None],
) -> list[tuple[str, dict[str, int]]]:
    """For each column of the chart, the number of responses of each class."""
    labels = [label for label, _ in BUCKETS] + [SLOWER]
    counts = {label: dict.fromkeys(CLASSES, 0) for label in labels}
    for entry in entries:
        if entry:
            counts[bucket(entry[1])][entry[0]] += 1
    return [(label, counts[label]) for label in labels]


def format_duration(delay: timedelta) -> str:
    """Two units at most: 45m, 3h 12m, 2d 4h."""
    minutes = round(delay.total_seconds() / 60)
    days, minutes = divmod(minutes, 1440)
    hours, minutes = divmod(minutes, 60)
    if days:
        return f"{days}d {hours}h" if hours else f"{days}d"
    if hours:
        return f"{hours}h {minutes}m" if minutes else f"{hours}h"
    return f"{minutes}m"


def summary(entries: list[tuple[str, timedelta] | None]) -> list[tuple[str, int, str]]:
    """(class, number, "average X, median Y") of each class that has responses."""
    lines = []
    for response in CLASSES:
        delays = [e[1] for e in entries if e and e[0] == response]
        if delays:
            average = timedelta(seconds=mean(d.total_seconds() for d in delays))
            lines.append(
                (
                    response,
                    len(delays),
                    f"average {format_duration(average)}, "
                    f"median {format_duration(median(delays))}",
                )
            )
    return lines


def scale(entries: list[tuple[str, timedelta] | None]) -> int:
    """How many responses one character of a bar stands for."""
    longest = max((sum(c.values()) for _, c in histogram(entries)), default=0)
    return max(1, math.ceil(longest / MAX_BAR))


def render(
    title: str,
    entries: list[tuple[str, timedelta] | None],
    paint: Callable[[str, str], str] = lambda text, response: text,
) -> list[str]:
    """The lines of the bar chart of one kind, stacked by who answered first.

    paint(text, class) colours the text of a class."""
    answered = [e for e in entries if e]
    lines = [
        f"{title} ({len(entries)}, {len(entries) - len(answered)} without response)"
    ]
    if not answered:
        return [*lines, "  no responses"]
    step = scale(entries)
    lines.append(
        "  " + "  ".join(paint(f"█ {response}", response) for response in CLASSES)
    )
    if step > 1:
        lines.append(f"  one bar character is up to {step} responses")
    rows = histogram(entries)
    width = max(len(label) for label, _ in rows) + 2
    for label, counts in rows:
        name = "> 3w" if label == SLOWER else f"<= {label}"
        bars = "".join(
            paint("█" * math.ceil(counts[response] / step), response)
            for response in CLASSES
        )
        numbers = " ".join(
            paint(str(counts[response]), response) for response in CLASSES
        )
        lines.append(f"  {name.rjust(width + 1)} | {bars} {numbers}")
    for response, number, text in summary(entries):
        lines.append(paint(f"  {response}: {number} responses, {text}", response))
    return lines
