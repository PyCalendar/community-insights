"""How long pull requests and issues wait for their first response."""

import math
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from statistics import NormalDist, mean, median, stdev

from github import Auth, Github

from .cache import ResponseCache, installed
from .contributors import (
    JOBS,
    PER_PAGE,
    REQUEST_DELAY,
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
NORMAL_95 = NormalDist().inv_cdf(0.95)  # 1.645 standard deviations
MAX_BAR = 40  # characters of the longest bar; longer ones are scaled down


def classify(login: str, association: str | None, bot: bool = False) -> str:
    """Whether a response is by a bot, an external person or a collaborator."""
    if bot or is_bot(login):
        return BOT
    return COLLABORATOR if (association or "").lower() in MEMBERS else EXTERNAL


# How many items are read with their first comments and reviews in one request,
# and how many comments or reviews of an item come with it. An item whose first
# ones are all by its author gets the next ones in another request.
PAGE = 50
INNER = 20
FOLLOW = 100  # per request, for what comes after
UTC_MAX = datetime.max.replace(tzinfo=UTC)

# The time until the first response of each class, for one pull request or issue.
Times = dict[str, timedelta]
FIELDS = {"prs": "pullRequests", "issues": "issues"}
STATES = "states: [APPROVED, CHANGES_REQUESTED, COMMENTED, DISMISSED]"  # not PENDING


def connection(field: str, after: bool = False) -> str:
    """The first comments or reviews of an item, or the ones after $after."""
    date = "createdAt" if field == "comments" else "submittedAt"
    arguments = "first: $inner"
    arguments += ", after: $after" if after else ""
    arguments += f", {STATES}" if field == "reviews" else ""
    return (
        f"{field}({arguments}) {{ pageInfo {{ hasNextPage endCursor }} "
        f"nodes {{ {date} author {{ login __typename }} authorAssociation }} }}"
    )


def list_query(kind: str) -> str:
    """A page of the pull requests or issues, the newest changes first: reading
    stops at what was read before."""
    reviews = connection("reviews") if kind == "prs" else ""
    return f"""
query($owner: String!, $name: String!, $after: String, $page: Int!, $inner: Int!) {{
  repository(owner: $owner, name: $name) {{
    {FIELDS[kind]}(first: $page, after: $after,
          orderBy: {{field: UPDATED_AT, direction: DESC}}) {{
      totalCount
      pageInfo {{ hasNextPage endCursor }}
      nodes {{ id number createdAt updatedAt author {{ login }}
               {connection("comments")} {reviews} }}
    }}
  }}
}}
"""


def more_query(field: str) -> str:
    """The next comments or reviews of an item."""
    found = connection(field, after=True)
    types = ["Issue", "PullRequest"] if field == "comments" else ["PullRequest"]
    on = " ".join(f"... on {name} {{ {found} }}" for name in types)
    return (
        f"query($id: ID!, $after: String, $inner: Int!) {{ node(id: $id) {{ {on} }} }}"
    )


def same_user(login: str, other: str | None) -> bool:
    """Handles are not case sensitive."""
    return login.lower() == (other or "").lower()


class ResponseCollector(Collector):
    """Reads when the pull requests and issues were first answered.

    GraphQL returns an item with its first comments and reviews, so a hundred
    pull requests need two requests instead of hundreds. What is read is
    remembered per repository and kind with the time of the newest change; the
    next run reads the items from the newest change back to that time only."""

    def graphql(self, query: str, **variables) -> dict:
        headers, data = self.send(
            "POST", "/graphql", input={"query": query, "variables": variables}
        )
        self.note_rate_limit(headers)
        if data.get("errors"):
            raise RuntimeError(f"GraphQL: {data['errors'][0].get('message')}")
        return data["data"]

    def first_responses(
        self, item: dict, field: str, connection: dict
    ) -> dict[str, datetime]:
        """The date of the first comment or review of each class by someone else
        than the author of the item. The next ones are read as long as a class is
        missing, so a bot that answers first does not hide the others."""
        owner = (item.get("author") or {}).get("login")
        found: dict[str, datetime] = {}
        while True:
            for node in connection["nodes"]:
                actor = node.get("author") or {}
                date = node.get("createdAt") or node.get("submittedAt")
                if actor.get("login") and not same_user(actor["login"], owner) and date:
                    response = classify(
                        actor["login"],
                        node.get("authorAssociation"),
                        actor.get("__typename") == "Bot",
                    )
                    found[response] = min(
                        parse_date(date), found.get(response, UTC_MAX)
                    )
            page = connection["pageInfo"]
            if not page["hasNextPage"] or len(found) == len(CLASSES):
                return found
            node = self.graphql(
                more_query(field), id=item["id"], after=page["endCursor"], inner=FOLLOW
            )["node"]
            connection = node[field]

    def read_items(
        self, prefix: str, name: str, kind: str, since: date | None = None
    ) -> list[list]:
        """[created, {class: seconds}] of the items of a kind created since the
        date (all if None).

        An item created since the date was changed since, too, so reading the
        newest changes down to that time finds all of them."""
        owner, repo = name.split("/", 1)
        key = self.cache and self.cache.key(
            self.token, f"graphql responses 2|{name}|{kind}"
        )
        limit = f"{since.isoformat()}T00:00:00Z" if since else ""
        stored = key and self.cache.recall(key)
        if stored:
            stored.setdefault("from", "")
        # A stored result that starts later than wanted cannot be extended.
        if not stored or (stored["from"] and stored["from"] > limit):
            stored = {"read": None, "from": limit, "items": {}}
        items: dict[str, list] = stored["items"]
        newest = stored["read"]  # the time of the newest change read
        stop = max(stored["read"] or "", limit)  # older changes are not read
        label = "pull requests" if kind == "prs" else "issues"
        changed = set()
        cursor, more, done = None, True, False
        while more and not done:
            found = self.graphql(
                list_query(kind),
                owner=owner,
                name=repo,
                after=cursor,
                page=PAGE,
                inner=INNER,
            )["repository"][FIELDS[kind]]
            for item in found["nodes"]:
                if item["updatedAt"] < stop:
                    done = True  # the older ones are unchanged or too old
                    break
                created = parse_date(item["createdAt"])
                responses = self.first_responses(item, "comments", item["comments"])
                if kind == "prs":
                    for response, date_ in self.first_responses(
                        item, "reviews", item["reviews"]
                    ).items():
                        responses[response] = min(
                            date_, responses.get(response, UTC_MAX)
                        )
                items[str(item["number"])] = [
                    item["createdAt"],
                    {
                        response: max((date_ - created).total_seconds(), 0)
                        for response, date_ in responses.items()
                    },
                ]
                changed.add(item["number"])
                newest = max(newest or "", item["updatedAt"])
            more, cursor = (
                found["pageInfo"]["hasNextPage"],
                found["pageInfo"]["endCursor"],
            )
            unchanged = ""
            if done:
                unchanged = (
                    ", the rest unchanged" if stored["read"] else ", the rest older"
                )
            total = found["totalCount"]
            self.say(f"{prefix}: {label} {len(changed)}/{total} read{unchanged}")
        self.skipped += len(items) - len(changed)
        if key:
            self.cache.remember(
                key, {"read": newest, "from": stored["from"], "items": items}
            )
        return [item for item in items.values() if item[0] >= limit]

    def collect_responses(
        self, number: int, count: int, name: str, since: date | None = None
    ) -> dict[str, list[Times]]:
        """Read one repository: per kind ("prs", "issues") one entry for each
        item, the time to the first response of each class that responded.
        """
        prefix = f"[{number}/{count}] {name}"
        result = {}
        for kind in FIELDS:
            with self.step("pull requests" if kind == "prs" else "issues"):
                items = self.read_items(prefix, name, kind, since)
            result[kind] = [
                {
                    response: timedelta(seconds=seconds)
                    for response, seconds in found.items()
                }
                for _, found in items
            ]
        return result


def collect_responses(
    token: str,
    repositories: Iterable[str],
    progress: Callable[[str], None] = lambda message: None,
    cache: ResponseCache | None = None,
    base_url: str = "https://api.github.com",
    jobs: int = JOBS,
    since: date | None = None,
) -> dict[str, list[Times]]:
    """The first responses of the pull requests ("prs") and issues ("issues").

    One entry per pull request or issue: for each class (bot, external,
    collaborator or higher) that responded, the time until its first response. A
    bot that is faster does not hide the others. Only those created since the
    date (if given) are included. Items are read with GraphQL; with a cache only
    those changed since the last run are read again.
    """
    repositories = list(repositories)
    result: dict[str, list[Times]] = {"prs": [], "issues": []}
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
                number, len(repositories), name, since
            ).items():
                result[kind] += entries
        collector.say(f"Done: {len(repositories)} repositories")
    return result


def bucket(delay: timedelta) -> str:
    """The label of the column of the chart a response time is counted in."""
    return next((label for label, limit in BUCKETS if delay <= limit), SLOWER)


def histogram(entries: list[Times]) -> list[tuple[str, dict[str, int]]]:
    """For each column of the chart, the number of first responses of each class."""
    labels = [label for label, _ in BUCKETS] + [SLOWER]
    counts = {label: dict.fromkeys(CLASSES, 0) for label in labels}
    for entry in entries:
        for response, delay in entry.items():
            counts[bucket(delay)][response] += 1
    return [(label, counts[label]) for label in labels]


def format_duration(delay: timedelta) -> str:
    """Two units at most: 45min, 3h 12min, 2d 4h (min is minutes)."""
    minutes = round(delay.total_seconds() / 60)
    days, minutes = divmod(minutes, 1440)
    hours, minutes = divmod(minutes, 60)
    if days:
        return f"{days}d {hours}h" if hours else f"{days}d"
    if hours:
        return f"{hours}h {minutes}min" if minutes else f"{hours}h"
    return f"{minutes}min"


TABLE_HEADER = ("class", "n", "fit", "average", "std error", "median", "95%")


def summary(entries: list[Times]) -> list[tuple[str, ...]]:
    """The rows (class, n, fit, average, std error, median, 95%) of a table, three
    for each class that has responses, with the times as text and "-" where
    there is none.

    - measured: the average and the median of the times, and the standard error
      of the average (the standard deviation s / sqrt(n); none for one time).
    - normal: the average and s of the times, so the standard error is
      s / sqrt(n), the median is the average and the 95th percentile
      average + 1.645 * s.
    - exponential: its maximum likelihood rate is 1 / average, so the average
      stays, the standard deviation is the average (standard error average /
      sqrt(n)), the median is average * ln 2 and the 95th percentile
      average * ln 20.
    """

    def show(value: float) -> str:
        return format_duration(timedelta(seconds=value))

    rows = []
    for response in CLASSES:
        seconds = [e[response].total_seconds() for e in entries if response in e]
        if not seconds:
            continue
        count = len(seconds)
        average = mean(seconds)
        deviation = stdev(seconds) if count > 1 else None
        shown = show(deviation / math.sqrt(count)) if deviation is not None else "-"
        head = (response, str(count))
        rows += [
            (*head, "measured", show(average), shown, show(median(seconds)), "-"),
            (
                *head,
                "normal",
                show(average),
                shown,
                show(average),
                show(average + NORMAL_95 * deviation) if deviation is not None else "-",
            ),
            (
                *head,
                "exponential",
                show(average),
                show(average / math.sqrt(count)),
                show(average * math.log(2)),
                show(average * math.log(20)),
            ),
        ]
    return rows


def table(rows: list[tuple[str, ...]]) -> list[tuple[str, str]]:
    """The header and the rows as aligned lines, with the class of each: the
    text columns are left aligned, the numbers right aligned."""
    widths = [max(len(r[i]) for r in [TABLE_HEADER, *rows]) for i in range(7)]
    left = {0, 2}

    def line(row: tuple[str, ...]) -> str:
        cells = [
            cell.ljust(width) if i in left else cell.rjust(width)
            for i, (cell, width) in enumerate(zip(row, widths, strict=True))
        ]
        return "  " + "  ".join(cells)

    return [("", line(TABLE_HEADER))] + [(row[0], line(row)) for row in rows]


def scale(entries: list[Times]) -> int:
    """How many responses one character of a bar stands for."""
    longest = max((sum(c.values()) for _, c in histogram(entries)), default=0)
    return max(1, math.ceil(longest / MAX_BAR))


def render(
    title: str,
    entries: list[Times],
    paint: Callable[[str, str], str] = lambda text, response: text,
) -> list[str]:
    """The lines of the bar chart of one kind and a table of the times.

    A row of the chart is a time, the number of first responses of each class
    in it, right aligned, and the bars of the classes stacked. paint(text,
    class) colours the text of a class."""
    silent = sum(1 for e in entries if not e)
    lines = [f"{title} ({len(entries)}, {silent} without any response)"]
    if silent == len(entries):
        return [*lines, "  no responses"]
    step = scale(entries)
    lines.append(
        "  " + "  ".join(paint(f"█ {response}", response) for response in CLASSES)
    )
    if step > 1:
        lines.append(f"  one bar character is up to {step} responses")
    rows = histogram(entries)
    names = ["> 3w" if label == SLOWER else f"<= {label}" for label, _ in rows]
    label_width = max(len(name) for name in names)
    number_width = max(len(str(n)) for _, counts in rows for n in counts.values())
    for name, (_, counts) in zip(names, rows, strict=True):
        numbers = " ".join(
            paint(str(counts[response]).rjust(number_width), response)
            for response in CLASSES
        )
        bars = "".join(
            paint("█" * math.ceil(counts[response] / step), response)
            for response in CLASSES
        )
        lines.append(f"  {name.rjust(label_width)}  {numbers} | {bars}")
    lines.append("")
    for response, line in table(summary(entries)):
        lines.append(paint(line, response) if response else line)
    return lines
