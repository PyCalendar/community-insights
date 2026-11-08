"""What a response is, and how long pull requests and issues waited for their first one.

This module holds the one definition of a response that every page uses (see
``docs/explanation/responses.rst``): a comment or a review by somebody else than the author,
or the merge or the close of the item by somebody else than the author. ``responses_to``
finds them; the other functions choose among them: the first one of each class of people,
the first one that is not of a bot, and whether an open item still waits for a collaborator.
"""

from collections.abc import Callable
from datetime import datetime, timedelta

from django.db.models.functions import Lower
from django.utils import timezone

from ..heavy import LOCK
from ..models import Event, Item
from .associations import more_privileged
from .response import Response
from .selection import items_in

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
SLOWER = "> 3w"

# The time in seconds until the first response of each class (by name), and under FIRST the
# time until the first response that is not of a bot: the first response of the item.
Times = dict[str, float]
FIRST = ""


def closers_of(rows) -> dict[tuple[int, str], tuple[str, bool]]:
    """The status and the bot mark of who merged or closed items, from their other events.

    Who merges or closes the item of somebody else may maintain the repository: without an
    event that shows a status, the status is ``collaborator``.

    Args:
        rows: (repository id, login) of who merged or closed.

    Returns:
        The status and whether GitHub marks them as a bot, by (repository id, login lowercase).
    """
    wanted = {(repository, login.lower()) for repository, login in rows}
    found = {key: ("", key[1].endswith("[bot]")) for key in wanted}
    events = (
        Event.objects.annotate(login=Lower("actor"))
        .filter(
            item__repository__in={repository for repository, _ in wanted},
            login__in={login for _, login in wanted},
        )
        .values_list("item__repository", "login", "association", "is_bot")
        .distinct()
    )
    for repository, login, association, is_bot in events:
        if (repository, login) in found:
            known, bot = found[repository, login]
            found[repository, login] = (more_privileged(known, association), bot or is_bot)
    return {key: (status or "collaborator", bot) for key, (status, bot) in found.items()}


def responses_to(
    items, since: datetime | None = None, until: datetime | None = None, login: str = ""
) -> dict[int, list[Response]]:
    """Every response to each item, in the order of time: the one definition of a response.

    A response is a comment or a review by somebody else than the author, or the merge or the
    close of the item by somebody else than the author, at the time it was closed. Closing
    their own item is no response: nobody answered. Whether a response of a bot counts is
    decided by those who use them, with ``bot_test``.

    Args:
        items: The pull requests and issues, as a query.
        since: Only responses from then on; None for all.
        until: Only responses before then; None for all.
        login: Only the responses of this person, in any case; "" for everybody's.

    Returns:
        The responses by the id of the item; an item without any has an empty list.
    """
    rows = list(
        items.values_list(
            "pk",
            "repository",
            "author",
            "created_at",
            "closed_at",
            "merged",
            "merged_by",
            "closed_by",
        )
    )
    info = {row[0]: row for row in rows}
    found: dict[int, list[Response]] = {pk: [] for pk in info}

    def wanted(actor: str, at: datetime) -> bool:
        if login and actor.lower() != login.lower():
            return False
        return (since is None or at >= since) and (until is None or at < until)

    events = (
        Event.objects.filter(item__in=info.keys())
        .exclude(kind=Event.OPENED)
        .order_by("at")
        .values_list("item_id", "actor", "association", "is_bot", "at", "kind", "state")
    )
    for pk, actor, association, is_bot, at, kind, state in events.iterator():
        _, _, author, created, *_ = info[pk]
        if actor.lower() != author.lower() and wanted(actor, at):
            seconds = max((at - created).total_seconds(), 0)
            found[pk].append(
                Response(actor, association.lower(), is_bot, at, seconds, kind, state or "")
            )
    closes = {}
    for pk, repository, author, created, closed, merged, merged_by, closed_by in rows:
        closer = merged_by if merged else closed_by
        if closed and closer and closer.lower() != author.lower() and wanted(closer, closed):
            closes[pk] = (repository, closer)
    statuses = closers_of(closes.values())
    for pk, (repository, closer) in closes.items():
        _, _, _, created, closed, merged, *_ = info[pk]
        association, is_bot = statuses[repository, closer.lower()]
        kind = Response.MERGE if merged else Response.CLOSE
        seconds = max((closed - created).total_seconds(), 0)
        found[pk].append(Response(closer, association, is_bot, closed, seconds, kind))
        found[pk].sort(key=lambda response: response.at)
    return found


def bot_test(classifier) -> Callable[[Response], bool]:
    """How to tell whether a response is of a bot.

    With classes of people, a bot is who is in the first class with the rule "is a bot"; if
    no class has that rule, nobody is. Without classes, a bot is who GitHub marks as one.

    Args:
        classifier: Decides the class of each actor; None for the marks of GitHub.

    Returns:
        A function that says whether a response is of a bot.
    """
    if classifier is None:
        return lambda response: response.is_bot
    bots = classifier.bot_class()
    if bots is None:
        return lambda response: False
    return lambda r: classifier(r.actor, r.association, r.is_bot) == bots


def first_by_class(responses: list[Response], classifier, is_bot=None) -> Times:
    """The seconds until the first response of each class of people, and of the item.

    The first response of a bot does not hide that of a maintainer: each class has its own.
    Under ``FIRST`` is the first response that is not of a bot.

    Args:
        responses: The responses to one item, in the order of time.
        classifier: Decides the class of each actor; an actor of no class is left out.
        is_bot: Tells the responses of bots (see ``bot_test``); None asks ``bot_test``.

    Returns:
        The seconds by the name of the class, and under ``FIRST``.
    """
    first = first_response(responses, is_bot or bot_test(classifier))
    times: Times = {FIRST: first.seconds} if first else {}
    for response in responses:
        person_class = classifier(response.actor, response.association, response.is_bot)
        if person_class is not None:
            times.setdefault(person_class.name, response.seconds)
    return times


def first_response(responses: list[Response], is_bot: Callable[[Response], bool]):
    """The first response that is not of a bot.

    Args:
        responses: The responses to one item, in the order of time.
        is_bot: Tells the responses of bots (see ``bot_test``).

    Returns:
        The response, None without one.
    """
    return next((r for r in responses if not is_bot(r)), None)


def waits(state: str, responses: list[Response], is_bot: Callable[[Response], bool]) -> bool:
    """Whether an item waits: it is open, and no collaborator or higher responded yet.

    Args:
        state: The state of the item: ``open`` or ``closed``.
        responses: Its responses.
        is_bot: Tells the responses of bots (see ``bot_test``).

    Returns:
        Whether it waits.
    """
    return state == "open" and not any(r.by_collaborator and not is_bot(r) for r in responses)


def response_entries(
    repositories, classifier, since: datetime | None = None, until: datetime | None = None
) -> dict[str, list[Times]]:
    """The time until the first response of each class, per item.

    Per kind, one entry for each item: the seconds until the first response of each class that
    responded (see ``responses_to``), so a bot that answers first does not hide the others.
    The items are those created in the time range.

    Args:
        repositories: The repositories.
        classifier: Decides the class of each actor.
        since: The start of the time range, None for the beginning.
        until: The end of the time range, excluded; None for now.

    Returns:
        The entries by kind: ``pr`` and ``issue``.
    """
    return response_times(repositories, classifier, since, until)[0]


def response_rows(
    repositories, classifier, since: datetime | None = None, until: datetime | None = None
) -> dict[str, list[tuple[datetime, Times, float]]]:
    """For each item: when it was created, its response times and how long it was observed.

    Args:
        repositories: The repositories.
        classifier: Decides the class of each actor.
        since: The start of the time range, None for the beginning.
        until: The end of the time range, excluded; None for now.

    Returns:
        By kind, for each item the time it was created, the seconds until the first response
        of each class (see ``response_entries``) and the seconds it was observed: until it was
        closed, or until now.
    """
    now = timezone.now()
    items = items_in(repositories, since, until)
    info = {
        pk: (kind, created, closed)
        for pk, kind, created, closed in items.values_list("id", "kind", "created_at", "closed_at")
    }
    found = responses_to(items)
    is_bot = bot_test(classifier)
    rows: dict[str, list[tuple[datetime, Times, float]]] = {Item.PR: [], Item.ISSUE: []}
    for pk, (kind, created, closed) in info.items():
        times = first_by_class(found[pk], classifier, is_bot)
        rows[kind].append((created, times, max(((closed or now) - created).total_seconds(), 0)))
    return rows


def response_times(
    repositories, classifier, since: datetime | None = None, until: datetime | None = None
) -> tuple[dict[str, list[Times]], dict[str, list[float]]]:
    """The response times and how long each item was observed.

    The entries of response_entries, and per kind for each item the seconds it was observed:
    until it was closed, or until now. An item without a response of a class waited at least
    that long for it (censored data).

    Args:
        repositories: The repositories.
        classifier: Decides the class of each actor.
        since: The start of the time range, None for the beginning.
        until: The end of the time range, excluded; None for now.

    Returns:
        The entries by kind, and the seconds each item was observed by kind.
    """
    rows = response_rows(repositories, classifier, since, until)
    result = {kind: [times for _, times, _ in found] for kind, found in rows.items()}
    observed = {kind: [seconds for _, _, seconds in found] for kind, found in rows.items()}
    return result, observed


def bucket(seconds: float) -> str:
    """The label of the bar of the chart a time falls into.

    Args:
        seconds: The time until the response.

    Returns:
        The label, such as ``3h``.
    """
    return next((label for label, limit in BUCKETS if seconds <= limit.total_seconds()), SLOWER)


def histogram(entries: list[Times], names: list[str]) -> list[tuple[str, dict[str, int]]]:
    """For each bar of the chart, how many first responses of each class fall into it.

    Args:
        entries: The seconds until the first response of each class, one dictionary per item.
        names: The classes to count.

    Returns:
        For each bar, its label and the number of each class.
    """
    labels = [label for label, _ in BUCKETS] + [SLOWER]
    counted = {label: dict.fromkeys(names, 0) for label in labels}
    for entry in entries:
        for name, seconds in entry.items():
            if name in names:
                counted[bucket(seconds)][name] += 1
    return [(label, counted[label]) for label in labels]


def percentile(values: list[float], p: float) -> float | None:
    """The p-th percentile (0-100), as `numpy.percentile` (linear); None without data.

    Args:
        values: The values.
        p: The percentile, 0 to 100.

    Returns:
        The value, or None.
    """
    with LOCK:  # see heavy.py
        import numpy

    if not len(values):
        return None
    return float(numpy.percentile(values, p))


def class_percentile(entries: list[Times], name: str | None, p: float) -> tuple[float | None, int]:
    """A percentile of the time until the first response.

    Percentile of the time until the first response of a class, or of the first response of the
    item if name is None (not of a bot, see ``responses_to``); and the number of responses.

    Args:
        entries: The seconds until the first response of each class, one dictionary per item.
        name: The class, None for the first response of the item (``FIRST``).
        p: The percentile, 0 to 100.

    Returns:
        The seconds, None without responses, and how many responses there are.
    """
    if name is None:
        seconds = [e[FIRST] for e in entries if FIRST in e]
    else:
        seconds = [e[name] for e in entries if name in e]
    return percentile(seconds, p), len(seconds)
