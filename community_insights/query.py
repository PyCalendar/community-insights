"""Queries on the contributors table.

Queries on the contributors table: a filter expression, sorting, columns, grouping and a chart of
the result.

An expression is parsed as a Python expression but never run: only the names of VARIABLES, numbers,
text in quotes, True, False, comparisons, and, or, not and parentheses are accepted. Example::

prs_merged >= 2 and days_last < 90 and not bot "berlin" in location or class == "maintainers"
"""

import ast
import difflib
import operator
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

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
    """Whole days since a time; infinite without one."""
    return float("inf") if date is None else max((now - date).days, 0)


def hours(seconds: float | None) -> float:
    """Seconds as hours with one decimal; infinite for none."""
    return float("inf") if seconds is None else round(seconds / 3600, 1)


# name: (what it is, "number" / "text" / "bool", how to get it)
VARIABLES: dict[str, tuple[str, str, Callable]] = {
    "login": ("the GitHub handle", "text", lambda c, now: c.login),
    "name": ("the name in the GitHub profile", "text", lambda c, now: c.name),
    "location": ("the location in the GitHub profile", "text", lambda c, now: c.location),
    "country": (
        "the country of the location (ISO code, such as DE)",
        "text",
        lambda c, now: locations.country_of(c.location) or "",
    ),
    "horizon_europe": (
        "True for locations in Horizon Europe",
        "bool",
        lambda c, now: locations.in_horizon_europe(c.location),
    ),
    "class": ("the class of people", "text", lambda c, now: c.klass),
    "bot": ("True for bots", "bool", lambda c, now: c.klass == "bot" or c.login.endswith("[bot]")),
    "prs_opened": ("pull requests opened", "number", lambda c, now: c.prs_opened),
    "prs_merged": ("pull requests opened and merged", "number", lambda c, now: c.prs_merged),
    "prs_closed": ("pull requests closed without merging", "number", lambda c, now: c.prs_closed),
    "prs_open": ("pull requests still open", "number", lambda c, now: c.prs_open),
    "issues_opened": ("issues opened", "number", lambda c, now: c.issues_opened),
    "issues_closed": ("issues opened and closed", "number", lambda c, now: c.issues_closed),
    "issues_open": ("issues opened and still open", "number", lambda c, now: c.issues_open),
    "comments": ("comments on items of others", "number", lambda c, now: c.comments),
    "reviews": ("reviews of pull requests of others", "number", lambda c, now: c.reviews),
    "activity": (
        "pull requests, issues, comments, reviews and commits",
        "number",
        lambda c, now: c.activity,
    ),
    "response_hours": (
        "median hours until their first response on items of others",
        "number",
        lambda c, now: hours(c.median_response),
    ),
    "active_months": ("months with any activity", "number", lambda c, now: c.active_months),
    "days_first": (
        "days since the first activity",
        "number",
        lambda c, now: days_since(c.first, now),
    ),
    "days_last": ("days since the last activity", "number", lambda c, now: days_since(c.last, now)),
}
NUMBERS = [name for name, (_, kind, _) in VARIABLES.items() if kind == "number"]
DEFAULT_COLUMNS = [
    "login",
    "class",
    "prs_opened",
    "prs_merged",
    "issues_opened",
    "comments",
    "reviews",
    "response_hours",
    "location",
    "days_last",
]
GROUPS = ("class", "location", "country", "horizon_europe", "bot")
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
    """The error for an unknown variable, with the names that are close."""
    close = difflib.get_close_matches(name, VARIABLES, n=3)
    hint = f" Did you mean {', '.join(close)}?" if close else ""
    return UnknownVariable(f"There is no variable {name!r}.{hint}")


def value(contributor: Contributor, name: str, now: datetime):
    """The value of a variable for a contributor."""
    if name not in VARIABLES:
        raise unknown(name)
    return VARIABLES[name][2](contributor, now)


def parse(text: str) -> Predicate:
    """Compile a filter expression; an empty one keeps everybody."""
    text = (text or "").strip()
    if not text:
        return lambda contributor, now: True
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError as error:
        raise QueryNotReadable(f"{text!r} cannot be read: {error.msg}.") from error

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
        raise NotAComparison(f"Not a comparison: {ast.get_source_segment(text, node)!r}.")

    def compare_chain(left, ops, right) -> Predicate:
        terms = [term(n) for n in (left, *right)]
        if not all(type(o) in OPERATORS for o in ops):
            raise UnsupportedComparison(f"Unsupported comparison in {text!r}.")
        compares = [OPERATORS[type(o)] for o in ops]
        kinds = {kind for kind, _ in terms}
        if len(kinds) > 1:
            raise TextComparedWithNumber(f"Text and numbers are compared in {text!r}.")
        allowed = TEXT_OPERATORS if "text" in kinds else NUMBER_OPERATORS
        if not all(isinstance(o, allowed) for o in ops):
            raise WrongOperatorForText(
                "Text is compared with ==, !=, in and not in; numbers with "
                f"==, !=, <, <=, >, >=: {text!r}."
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
            f"Expected a variable, a number or text, found {ast.get_source_segment(text, node)!r}."
        )

    return build(tree.body)


def parse_columns(text: str) -> list[str]:
    """Columns separated by spaces or commas; the default if empty."""
    names = [n for n in (text or "").replace(",", " ").split() if n]
    for name in names:
        if name not in VARIABLES:
            raise unknown(name)
    return names or list(DEFAULT_COLUMNS)


def parse_sort(text: str) -> tuple[str, bool]:
    """``-prs_merged`` (descending) or ``login`` / ``+login`` (ascending)."""
    text = (text or "-activity").strip()
    descending = text.startswith("-")
    name = text.lstrip("+-")
    if name not in VARIABLES:
        raise unknown(name)
    return name, descending


@dataclass
class Result:
    """The result of a query: the rows, the people, the groups and how many there were."""

    columns: list[str]
    rows: list[list]  # values in the order of the columns
    contributors: list[Contributor]
    groups: list[tuple[str, int, dict[str, float]]]  # (group, people, sums of the numbers)
    total: int


def run(
    contributors: list[Contributor],
    now: datetime,
    where: str = "",
    sort: str = "",
    columns: str = "",
    group: str = "",
) -> Result:
    """Filter, sort and group the contributors with a query; InvalidQuery if it cannot be used."""
    keep = parse(where)
    names = parse_columns(columns)
    by, descending = parse_sort(sort)
    if group and group not in GROUPS:
        raise UnknownGroup(f"Group by one of {', '.join(GROUPS)}, not {group!r}.")
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
