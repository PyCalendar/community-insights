"""Queries on the contributors table.

Queries on the contributors table: a filter expression, sorting, columns, grouping and a chart of
the result.

An expression is parsed as a Python expression but never run: only the names of VARIABLES, numbers,
text in quotes, True, False, comparisons, and, or, not and parentheses are accepted. Examples::

    prs_merged >= 2 and days_last < 90 and not user_bot
    "berlin" in user_location or user_class == "maintainers"
"""

import ast
import difflib
import operator
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from django.utils.translation import gettext, gettext_lazy

from . import locations
from .errors import (
    NotAComparison,
    NotAValue,
    QueryNotReadable,
    TextComparedWithNumber,
    UnknownGroup,
    UnknownVariable,
    UnsupportedComparison,
    WrongOperatorForText,
)
from .stats import Contributor


def days_since(date: datetime | None, now: datetime) -> float:
    """Whole days since a time; infinite without one.

    Args:
        date: A time, or None.
        now: The time now.

    Returns:
        The days, at least 0; infinite for None.
    """
    return float("inf") if date is None else max((now - date).days, 0)


def infinite_if_none(value: float | None) -> float:
    """A number, infinite for none, so that missing values sort last.

    Args:
        value: The number, or None.

    Returns:
        The number, or infinity.
    """
    return float("inf") if value is None else value


def hours(seconds: float | None) -> float:
    """Seconds as hours with one decimal; infinite for none.

    Args:
        seconds: The seconds, or None.

    Returns:
        The hours; infinite for None.
    """
    return float("inf") if seconds is None else round(seconds / 3600, 1)


# name: (what it is, "number" / "text" / "bool", how to get it). The names are those of the
# command line tool before (git history, 239c258): grouped by a prefix, the unit first
# (user_, commits_, prs_, issues_, comments_, actions_, activity_, hours_, days_, months_).
VARIABLES: dict[str, tuple[Any, str, Callable]] = {
    "user_handle": (gettext_lazy("the GitHub handle"), "text", lambda c, now: c.login),
    "user_name": (gettext_lazy("the name in the GitHub profile"), "text", lambda c, now: c.name),
    "user_location": (
        gettext_lazy("the location in the GitHub profile"),
        "text",
        lambda c, now: c.location,
    ),
    "user_country": (
        gettext_lazy("the country of the location (ISO code, such as DE)"),
        "text",
        lambda c, now: locations.country_of(c.location) or "",
    ),
    "user_horizon_europe": (
        gettext_lazy("True for locations in Horizon Europe"),
        "bool",
        lambda c, now: locations.in_horizon_europe(c.location),
    ),
    "user_class": (gettext_lazy("the class of people"), "text", lambda c, now: c.klass),
    "user_bot": (
        gettext_lazy("True for bots"),
        "bool",
        lambda c, now: c.klass == "bot" or c.login.endswith("[bot]"),
    ),
    "user_association": (
        gettext_lazy("the most privileged status seen, such as member or contributor"),
        "text",
        lambda c, now: c.association,
    ),
    "commits_total": (gettext_lazy("commits"), "number", lambda c, now: c.commits),
    "prs_total": (gettext_lazy("pull requests opened"), "number", lambda c, now: c.prs_opened),
    "prs_merged": (
        gettext_lazy("pull requests opened and merged"),
        "number",
        lambda c, now: c.prs_merged,
    ),
    "prs_unmerged": (
        gettext_lazy("pull requests opened and closed without merging"),
        "number",
        lambda c, now: c.prs_closed,
    ),
    "prs_closed": (
        gettext_lazy("pull requests opened and closed, merged or not"),
        "number",
        lambda c, now: c.prs_merged + c.prs_closed,
    ),
    "prs_open": (gettext_lazy("pull requests still open"), "number", lambda c, now: c.prs_open),
    "prs_commented": (
        gettext_lazy("pull requests of others commented on"),
        "number",
        lambda c, now: len(c.prs_commented),
    ),
    "prs_reviewed": (
        gettext_lazy("pull requests of others reviewed"),
        "number",
        lambda c, now: len(c.prs_reviewed),
    ),
    "issues_opened": (gettext_lazy("issues opened"), "number", lambda c, now: c.issues_opened),
    "issues_open": (
        gettext_lazy("issues opened and still open"),
        "number",
        lambda c, now: c.issues_open,
    ),
    "issues_closed": (
        gettext_lazy("issues opened and closed"),
        "number",
        lambda c, now: c.issues_closed,
    ),
    "issues_commented": (
        gettext_lazy("issues of others commented on"),
        "number",
        lambda c, now: len(c.issues_commented),
    ),
    "comments_total": (
        gettext_lazy("comments on items of others"),
        "number",
        lambda c, now: c.comments,
    ),
    "actions_merges": (
        gettext_lazy("pull requests merged by them"),
        "number",
        lambda c, now: c.merges,
    ),
    "activity_total": (
        gettext_lazy("pull requests, issues, comments, reviews and commits"),
        "number",
        lambda c, now: c.activity,
    ),
    "hours_to_respond": (
        gettext_lazy("median hours until their first response on items of others"),
        "number",
        lambda c, now: hours(c.median_response),
    ),
    "days_to_merge": (
        gettext_lazy("median days until their pull requests were merged"),
        "number",
        lambda c, now: infinite_if_none(c.days_to_merge),
    ),
    "days_first": (
        gettext_lazy("days since the first activity"),
        "number",
        lambda c, now: days_since(c.first, now),
    ),
    "days_last": (
        gettext_lazy("days since the last activity"),
        "number",
        lambda c, now: days_since(c.last, now),
    ),
    "months_active": (
        gettext_lazy("months with any activity"),
        "number",
        lambda c, now: c.active_months,
    ),
}
NUMBERS = [name for name, (_, kind, _) in VARIABLES.items() if kind == "number"]
DEFAULT_COLUMNS = [
    "user_handle",
    "user_class",
    "commits_total",
    "prs_merged",
    "issues_opened",
    "comments_total",
    "prs_reviewed",
    "hours_to_respond",
    "user_location",
    "days_last",
]
GROUPS = (
    "user_class",
    "user_association",
    "user_location",
    "user_country",
    "user_horizon_europe",
    "user_bot",
)
# variables that are a part of another one: shown as "part/total", such as 3/5 merged
FRACTIONS = {
    "prs_merged": "prs_total",
    "prs_unmerged": "prs_total",
    "prs_closed": "prs_total",
    "prs_open": "prs_total",
    "issues_open": "issues_opened",
    "issues_closed": "issues_opened",
}
# the names before the names of the command line tool came back, for saved queries
RENAMED = {
    "login": "user_handle",
    "name": "user_name",
    "location": "user_location",
    "country": "user_country",
    "horizon_europe": "user_horizon_europe",
    "class": "user_class",
    "bot": "user_bot",
    "prs_opened": "prs_total",
    "comments": "comments_total",
    "reviews": "prs_reviewed",
    "activity": "activity_total",
    "response_hours": "hours_to_respond",
    "active_months": "months_active",
}
OPERATORS = {
    ast.GtE: operator.ge,
    ast.LtE: operator.le,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Gt: operator.gt,
    ast.Lt: operator.lt,
    ast.In: lambda needle, text: needle in text,
    ast.NotIn: lambda needle, text: needle not in text,
}
TEXT_OPERATORS = (ast.Eq, ast.NotEq, ast.In, ast.NotIn)
NUMBER_OPERATORS = (ast.Eq, ast.NotEq, ast.GtE, ast.LtE, ast.Gt, ast.Lt)
Predicate = Callable[[Contributor, datetime], bool]


def unknown(name: str) -> UnknownVariable:
    """The error for an unknown variable, with the names that are close.

    Args:
        name: The name that is no variable.

    Returns:
        The error, to raise.
    """
    close = difflib.get_close_matches(name, VARIABLES, n=3)
    message = gettext("There is no variable %(name)s.") % {"name": repr(name)}
    if name in RENAMED:
        message += " " + gettext("It is called %(new)s now.") % {"new": RENAMED[name]}
    elif close:
        message += " " + gettext("Did you mean %(names)s?") % {"names": ", ".join(close)}
    return UnknownVariable(message)


def value(contributor: Contributor, name: str, now: datetime):
    """The value of a variable for a contributor.

    Args:
        contributor: The contributor.
        name: The name of the variable.
        now: The time now, for the variables of days.

    Returns:
        The value: text, a number or True and False.

    Raises:
        UnknownVariable: If the name is no variable.
    """
    if name not in VARIABLES:
        raise unknown(name)
    return VARIABLES[name][2](contributor, now)


def parse(text: str) -> Predicate:
    """Compile a filter expression; an empty one keeps everybody.

    Args:
        text: The expression, such as ``prs_merged >= 2 and not bot``.

    Returns:
        A function of a contributor and the time now: whether the contributor matches.

    Raises:
        QueryNotReadable: If the text is no expression.
        UnknownVariable: If a name is no variable.
        NotAComparison: If a part compares nothing.
        NotAValue: If a side of a comparison is no variable, number or text.
        UnsupportedComparison: If an operator cannot be used.
        TextComparedWithNumber: If text is compared with a number.
        WrongOperatorForText: If text is compared with ``<`` or ``>``.
    """
    text = (text or "").strip()
    if not text:
        return lambda contributor, now: True
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError as error:
        raise QueryNotReadable(
            gettext("%(text)s cannot be read: %(reason)s.")
            % {"text": repr(text), "reason": error.msg}
        ) from error

    def build(node: ast.expr) -> Predicate:
        match node:
            case ast.BoolOp(op=ast.And(), values=values):
                terms = [build(v) for v in values]
                return lambda c, now: all(t(c, now) for t in terms)
            case ast.BoolOp(op=ast.Or(), values=values):
                terms = [build(v) for v in values]
                return lambda c, now: any(t(c, now) for t in terms)
            case ast.UnaryOp(op=ast.Not(), operand=operand):
                inner = build(operand)
                return lambda c, now: not inner(c, now)
            case ast.Name(id=name) if name in VARIABLES and VARIABLES[name][1] == "bool":
                return lambda c, now: bool(value(c, name, now))
            case ast.Compare(left=left, ops=ops, comparators=right):
                return compare_chain(left, ops, right)
            case ast.Name(id=name) if name not in VARIABLES:
                raise unknown(name)
        raise NotAComparison(
            gettext("Not a comparison: %(part)s.")
            % {"part": repr(ast.get_source_segment(text, node))}
        )

    def compare_chain(left, ops, right) -> Predicate:
        terms = [term(n) for n in (left, *right)]
        if not all(type(o) in OPERATORS for o in ops):
            raise UnsupportedComparison(
                gettext("Unsupported comparison in %(text)s.") % {"text": repr(text)}
            )
        compares = [OPERATORS[type(o)] for o in ops]
        kinds = {kind for kind, _ in terms}
        if len(kinds) > 1:
            raise TextComparedWithNumber(
                gettext("Text and numbers are compared in %(text)s.") % {"text": repr(text)}
            )
        allowed = TEXT_OPERATORS if "text" in kinds else NUMBER_OPERATORS
        if not all(isinstance(o, allowed) for o in ops):
            raise WrongOperatorForText(
                gettext(
                    "Text is compared with ==, !=, in and not in; numbers with "
                    "==, !=, <, <=, >, >=: %(text)s."
                )
                % {"text": repr(text)}
            )
        getters = [get for _, get in terms]
        return lambda c, now: all(
            compare(a(c, now), b(c, now))
            for compare, a, b in zip(compares, getters, getters[1:], strict=False)
        )

    def term(node: ast.expr):
        match node:
            case ast.Name(id=name) if name in VARIABLES:
                kind = VARIABLES[name][1]
                if kind == "text":
                    return "text", lambda c, now: str(value(c, name, now)).lower()
                return "number", lambda c, now: value(c, name, now)
            case ast.Name(id=name):
                raise unknown(name)
            case ast.Constant(value=str() as literal):
                return "text", lambda c, now: literal.lower()
            case ast.Constant(value=bool() | int() | float() as number):
                return "number", lambda c, now: number
            case ast.UnaryOp(op=ast.USub(), operand=ast.Constant(value=int() | float() as number)):
                return "number", lambda c, now: -number
        raise NotAValue(
            gettext("Expected a variable, a number or text, found %(part)s.")
            % {"part": repr(ast.get_source_segment(text, node))}
        )

    return build(tree.body)


def parse_columns(text: str) -> list[str]:
    """Columns separated by spaces or commas; the default if empty.

    Args:
        text: The names of the variables, separated by spaces or commas.

    Returns:
        The names, or the default columns for an empty text.

    Raises:
        UnknownVariable: If a name is no variable.
    """
    names = [n for n in (text or "").replace(",", " ").split() if n]
    for name in names:
        if name not in VARIABLES:
            raise unknown(name)
    return names or list(DEFAULT_COLUMNS)


def parse_sort(text: str) -> tuple[str, bool]:
    """``-prs_merged`` (descending) or ``login`` / ``+login`` (ascending).

    Args:
        text: A variable, ``-`` before it for the biggest first; empty for ``-activity``.

    Returns:
        The variable and whether the biggest come first.

    Raises:
        UnknownVariable: If the name is no variable.
    """
    text = (text or "-activity_total").strip()
    descending = text.startswith("-")
    name = text.lstrip("+-")
    if name not in VARIABLES:
        raise unknown(name)
    return name, descending


@dataclass
class Result:
    """The result of a query: the rows, the people, the groups and how many there were.

    Attributes:
        columns: The variables shown, in their order.
        rows: The values of the columns, one list per person.
        contributors: The people shown, in the order of the rows.
        groups: For a grouping: the value, the number of people and the sums of the numbers.
        total: How many people there were before the filter.
    """

    columns: list[str]
    rows: list[list]  # values in the order of the columns
    contributors: list[Contributor]
    groups: list[tuple[str, int, dict[str, float]]]  # (group, people, sums of the numbers)
    total: int


def check(parameters: dict) -> None:
    """Check a query without running it, so that a mistake is told at once.

    Args:
        parameters: The fields of the query: where, sort, columns and group.

    Raises:
        InvalidQuery: If a part cannot be used.

    Examples:
        >>> check({"where": "prs_total > 1", "sort": "-prs_merged", "columns": "", "group": ""})
    """
    parse(parameters.get("where", ""))
    parse_columns(parameters.get("columns", ""))
    parse_sort(parameters.get("sort", ""))
    group = parameters.get("group", "")
    if group and group not in GROUPS:
        raise UnknownGroup(
            gettext("Group by one of %(groups)s, not %(group)s.")
            % {"groups": ", ".join(GROUPS), "group": repr(group)}
        )


def run(
    contributors: list[Contributor],
    now: datetime,
    where: str = "",
    sort: str = "",
    columns: str = "",
    group: str = "",
) -> Result:
    """Filter, sort and group the contributors with a query; InvalidQuery if it cannot be used.

    Args:
        contributors: The contributors.
        now: The time now, for the variables of days.
        where: The filter expression; empty for everybody.
        sort: The variable to sort by, ``-`` before it for the biggest first.
        columns: The variables to show, separated by spaces; empty for the default ones.
        group: A variable of ``GROUPS`` to sum the numbers by; empty for no groups.

    Returns:
        The columns, the rows, the contributors and the groups.

    Raises:
        UnknownGroup: If the group is not one of ``GROUPS``.
        InvalidQuery: If the filter, the sorting or the columns cannot be used.
    """
    keep = parse(where)
    names = parse_columns(columns)
    by, descending = parse_sort(sort)
    if group and group not in GROUPS:
        raise UnknownGroup(
            gettext("Group by one of %(groups)s, not %(group)s.")
            % {"groups": ", ".join(GROUPS), "group": repr(group)}
        )
    chosen = [c for c in contributors if keep(c, now)]

    def key(c):
        found = value(c, by, now)
        return (
            (found.lower(), c.login.lower()) if isinstance(found, str) else (found, c.login.lower())
        )

    chosen.sort(key=key, reverse=descending)
    groups = []
    if group:
        sums: dict[str, dict] = {}
        for c in chosen:
            label = str(value(c, group, now)) or "(none)"
            entry = sums.setdefault(label, {"people": 0, **dict.fromkeys(NUMBERS, 0.0)})
            entry["people"] += 1
            for name in NUMBERS:
                number = value(c, name, now)
                if number != float("inf"):
                    entry[name] += number
        groups = sorted(
            ((label, e.pop("people"), e) for label, e in sums.items()),
            key=lambda g: (-g[1], g[0]),
        )
    return Result(
        names,
        [[value(c, n, now) for n in names] for c in chosen],
        chosen,
        groups,
        len(contributors),
    )
