"""The data behind the statistics as tables, to check them with scipy, pandas or a spreadsheet.

See docs/how-to/verify.rst.
"""

import csv
import io
import json
import re
from datetime import UTC, datetime

from django.utils import timezone

from . import stats
from .errors import UnknownTable
from .models import Commit, Event

TABLES = ("responses", "items", "events", "commits", "contributors")


def column(name: str) -> str:
    """The column of the seconds until the first response of a class."""
    return "seconds_" + re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def iso(value: datetime | None) -> str:
    """A time as ISO 8601 in UTC with Z; empty for none."""
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z") if value else ""


def responses(
    repositories, classifier, class_names: list[str], since=None, until=None
) -> list[dict]:
    """The time until the first response of each item, per class.

    One row per pull request or issue: the seconds until the first response of each class (empty
    if there was none) and of anybody. Without a response the time is censored:
    `observed_seconds` says how long it was waited for, until it was closed or until now.
    """
    now = timezone.now()
    items = list(
        stats.items_in(repositories, since, until)
        .select_related("repository")
        .order_by("repository__full_name", "kind", "number")
    )
    first = {item.pk: {} for item in items}
    by_pk = {item.pk: item for item in items}
    events = (
        Event.objects.filter(item__in=by_pk.keys())
        .exclude(kind=Event.OPENED)
        .order_by("at")
        .values_list("item_id", "actor", "association", "is_bot", "at")
    )
    for pk, actor, association, bot, at in events.iterator():
        item = by_pk[pk]
        if actor.lower() == item.author.lower():
            continue
        seconds = max((at - item.created_at).total_seconds(), 0)
        first[pk].setdefault("", seconds)
        person_class = classifier(actor, association, bot)
        if person_class is not None:
            first[pk].setdefault(person_class.name, seconds)
    rows = []
    for item in items:
        found = first[item.pk]
        end = item.closed_at or now
        row = {
            "repository": item.repository.full_name,
            "kind": item.kind,
            "number": item.number,
            "author": item.author,
            "created_at": iso(item.created_at),
            "state": item.state,
            "merged": int(item.merged),
            "closed_at": iso(item.closed_at),
            "responded": int("" in found),
            "seconds_any": found.get(""),
            "observed_seconds": max((end - item.created_at).total_seconds(), 0),
        }
        for name in class_names:
            row[column(name)] = found.get(name)
        rows.append(row)
    return rows


def items(repositories, since=None, until=None) -> list[dict]:
    """The pull requests and issues created in the time range, one row each."""
    return [
        {
            "repository": item.repository.full_name,
            "kind": item.kind,
            "number": item.number,
            "title": item.title,
            "author": item.author,
            "author_association": item.author_association,
            "author_is_bot": int(item.author_is_bot),
            "state": item.state,
            "merged": int(item.merged),
            "merged_by": item.merged_by,
            "created_at": iso(item.created_at),
            "updated_at": iso(item.updated_at),
            "closed_at": iso(item.closed_at),
        }
        for item in stats.items_in(repositories, since, until)
        .select_related("repository")
        .order_by("repository__full_name", "kind", "number")
    ]


def events(repositories, since=None, until=None) -> list[dict]:
    """The openings, comments and reviews in the time range, one row each."""
    return [
        {
            "repository": event.item.repository.full_name,
            "item_kind": event.item.kind,
            "number": event.item.number,
            "kind": event.kind,
            "actor": event.actor,
            "association": event.association,
            "is_bot": int(event.is_bot),
            "at": iso(event.at),
        }
        for event in stats.events_in(
            Event.objects.filter(item__repository__in=repositories), since, until
        )
        .select_related("item__repository")
        .order_by("at")
    ]


def commits(repositories, since=None, until=None) -> list[dict]:
    """The commits in the time range, oldest first, one row each."""
    found = Commit.objects.filter(repository__in=repositories).select_related("repository")
    if since:
        found = found.filter(at__gte=since)
    if until:
        found = found.filter(at__lt=until)
    return [
        {
            "repository": c.repository.full_name,
            "sha": c.sha,
            "author": c.author,
            "author_name": c.author_name,
            "at": iso(c.at),
        }
        for c in found.order_by("at")
    ]


def contributors(repositories, classifier, since=None, until=None) -> list[dict]:
    """The contributors table: what each person did in the time range."""
    return [
        {
            "login": p.login,
            "class": p.klass,
            "name": p.name,
            "location": p.location,
            "prs_opened": p.prs_opened,
            "prs_merged": p.prs_merged,
            "prs_closed_unmerged": p.prs_closed,
            "prs_open": p.prs_open,
            "issues_opened": p.issues_opened,
            "issues_closed": p.issues_closed,
            "issues_open": p.issues_open,
            "comments": p.comments,
            "reviews": p.reviews,
            "commits": p.commits,
            "median_response_seconds": p.median_response,
            "first_activity": iso(p.first),
            "last_activity": iso(p.last),
            "active_months": p.active_months,
        }
        for p in sorted(
            stats.contributors(repositories, classifier, since, until),
            key=lambda p: p.login.lower(),
        )
    ]


def table(
    name: str, repositories, classifier, class_names: list[str], since=None, until=None
) -> list[dict]:
    """A table of the data, of the items created (events made) in the time range."""
    if name == "responses":
        return responses(repositories, classifier, class_names, since, until)
    if name == "items":
        return items(repositories, since, until)
    if name == "events":
        return events(repositories, since, until)
    if name == "commits":
        return commits(repositories, since, until)
    if name == "contributors":
        return contributors(repositories, classifier, since, until)
    raise UnknownTable(f"There is no table {name!r}.")


# the tables a table is made from: the extra sheets of its ODS
SOURCES = {
    "responses": ("items", "events"),
    "items": ("events",),
    "events": ("items",),
    "commits": (),
    "contributors": ("items", "events", "commits"),
}


def about_rows(about: dict) -> list[dict]:
    """What the export is: one row per fact, lists joined."""
    return [
        {
            "name": name,
            "value": ", ".join(map(str, value)) if isinstance(value, list | tuple) else value,
        }
        for name, value in about.items()
    ]


def workbook(
    name: str, repositories, classifier, class_names, since, until, about: dict, first=None
) -> list[tuple[str, list[dict]]]:
    """The sheets of the ODS of a table.

    The sheets of the ODS of a table: the table (or `first`, e.g. the result of a query), the
    tables it was made from, and what the export is.
    """
    sheets = list(
        first or [(name, table(name, repositories, classifier, class_names, since, until))]
    )
    if first:
        sheets.append((name, table(name, repositories, classifier, class_names, since, until)))
    for source in SOURCES.get(name, ()):
        sheets.append((source, table(source, repositories, classifier, class_names, since, until)))
    sheets.append(("about", about_rows(about)))
    return sheets


def to_csv(rows: list[dict]) -> str:
    """Rows as CSV with a header; None becomes an empty cell."""
    buffer = io.StringIO()
    if rows:
        writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: "" if v is None else v for k, v in row.items()})
    return buffer.getvalue()


def to_json(rows: list[dict], about: dict) -> str:
    """Rows as JSON, with what the export is."""
    return json.dumps({**about, "rows": rows}, indent=1, ensure_ascii=False)
