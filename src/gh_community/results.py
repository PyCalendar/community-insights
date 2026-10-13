"""Storing contributor results as CSV files and filtering them again."""

import ast
import csv
import io
import operator
import re
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path

from .contributors import ASSOCIATIONS, COLUMN_DEFS, is_bot, unknown

# The columns of the file, grouped by prefix. What can be calculated from them is
# not stored: prs_total, prs_closed, issues_closed, user_bot, days_first and
# days_last.
FIELDS = (
    "user_handle",
    "user_association",
    "commits_total",
    "prs_open",
    "prs_merged",
    "prs_unmerged",
    "prs_commented",
    "prs_reviewed",
    "prs_approved",
    "prs_changes_requested",
    "issues_opened",
    "issues_open",
    "issues_commented",
    "comments_total",
    "actions_merges",
    "actions_closes",
    "actions_labels",
    "days_to_merge",
    "months_active",
    "date_first",
    "date_last",
)
TEXT_FIELDS = ("user_handle", "user_association")
DATE_FIELDS = ("date_first", "date_last")
# a missing (empty) value of these is None, not 0
NULLABLE_FIELDS = ("days_to_merge",)
# the names of the columns in files written before the rename
OLD_NAMES = {
    "user_handle": "handle",
    "user_association": "association",
    "prs_open": "open_prs",
    "prs_merged": "merged",
    "prs_unmerged": "unmerged",
    "prs_commented": "pr_commented",
    "prs_reviewed": "reviewed",
    "prs_approved": "approved",
    "prs_changes_requested": "changes_requested",
    "issues_opened": "opened",
    "issues_open": "open_issues",
    "issues_commented": "commented",
    "actions_merges": "merges",
    "actions_closes": "closes",
    "actions_labels": "labels",
    "days_to_merge": "merge_days",
    "months_active": "active_months",
    "date_first": "first_activity",
    "date_last": "activity",
    "prs_total": "prs",
    "commits_total": "commits",
    "comments_total": "comments",
}
# The variables of the expressions, by group, with what they mean. They are the
# columns of the file and the table, plus what is calculated from them. The
# days_ ones are infinite if there is no data.
VARIABLES = {
    "user_handle": "text: the GitHub login",
    "user_association": "text, always lowercase, ordered by privilege: owner > "
    "member > collaborator > contributor > first_timer > first_time_contributor "
    "> mannequin > none > empty; the most privileged seen",
    "user_bot": "True if the handle contains [bot] or is Copilot, else False",
    "commits_total": "commits in the contributors list",
    "prs_total": "pull requests opened, in total",
    "prs_open": "pull requests opened and still open",
    "prs_merged": "pull requests opened and merged",
    "prs_unmerged": "pull requests opened and closed without merging",
    "prs_closed": "pull requests opened and closed (merged + unmerged)",
    "prs_commented": "pull requests of others commented on",
    "prs_reviewed": "pull requests of others reviewed",
    "prs_approved": "pull requests of others approved",
    "prs_changes_requested": "pull requests of others with changes requested",
    "issues_opened": "issues opened",
    "issues_open": "issues opened and still open",
    "issues_closed": "issues opened and closed",
    "issues_commented": "issues of others commented on",
    "comments_total": "all comments written",
    "actions_merges": "pull requests merged by them",
    "actions_closes": "issues and pull requests closed by them, other than by merging",
    "actions_labels": "labels set by them",
    "days_first": "days since the first activity",
    "days_last": "days since the last activity",
    "days_to_merge": "median days until their pull requests were merged",
    "months_active": "months with any activity",
}
# The associations can be written without quotes with this prefix:
# user_association >= association_member
ASSOCIATION_PREFIX = "association_"
ASSOCIATION_NAMES = tuple(ASSOCIATION_PREFIX + a for a in ASSOCIATIONS)
# the variables that are text, not numbers
TEXT_VARIABLES = ("user_handle", "user_association")


def variable_doc(name: str) -> str | None:
    """What the variable means; None if there is no such variable."""
    return VARIABLES.get(name)


EXPRESSION_HELP = (
    "Expressions, for example "
    "'prs_merged<10 and (days_last < 100 or issues_opened > 0)':\n\n"
    "Variables (whole numbers, except user_bot which is True or False and the "
    "text ones, which are compared in any case with ==, !=, in and not in):\n"
    + "\n".join(f"  {name:<22}{doc}" for name, doc in sorted(VARIABLES.items()))
    + "\n\nComparisons: >= <= == != > < (also chained, 1 < days_last < 9)."
    "\nText: == and != (equal), in and not in (the left text is part of the "
    "right one), for example '\"[bot]\" in user_handle'. user_association can "
    "also be compared by privilege with the association names, written as text "
    "or with the prefix association_: 'user_association >= association_member', "
    "'user_association == \"owner\"'."
    "\nOperators: and, or, not and parentheses; not binds tightest, then and, "
    "then or."
    "\nThere are no functions."
)
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
TIMESTAMP = "%Y-%m-%d-%H-%M-%S"
SUFFIX = ".csv"


def result_name(repositories: Iterable[str], now: datetime) -> str:
    """org-repo-yyyy-mm-dd-hh-mm-ss; several repositories are joined with _."""
    repos = "_".join(r.replace("/", "-") for r in repositories)
    return f"{repos}-{now.strftime(TIMESTAMP)}"


def result_path(directory: Path, name: str) -> Path:
    return directory / (name if name.endswith(SUFFIX) else name + SUFFIX)


def list_results(directory: Path) -> list[str]:
    """The names of the stored results, oldest first within a repository."""
    return sorted(p.stem for p in directory.glob("*" + SUFFIX) if p.is_file())


def write_result(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    f: (row[f].isoformat() if row[f] else "")
                    if f in DATE_FIELDS
                    else ""
                    if row[f] is None
                    else row[f]
                    for f in FIELDS
                }
            )


def _read_row(record: dict) -> dict:
    """One row; columns that the file lacks are 0, "" or None.

    Files written before the columns were renamed are read, too."""

    def get(field: str) -> str:
        return record.get(field) or record.get(OLD_NAMES.get(field, "")) or ""

    row = {}
    for field in FIELDS:
        text = get(field)
        if field in TEXT_FIELDS:
            row[field] = text.lower() if field == "user_association" else text
        elif field in DATE_FIELDS:
            row[field] = datetime.fromisoformat(text) if text else None
        elif field in NULLABLE_FIELDS:
            row[field] = float(text) if text else None
        else:
            row[field] = int(text or 0)
    # very old files have a total instead of the pull requests that are open
    total = get("prs_total")
    row["prs_total"] = (
        int(total)
        if total
        else row["prs_open"] + row["prs_merged"] + row["prs_unmerged"]
    )
    return row


def read_result(path: Path) -> list[dict]:
    with path.open(newline="") as file:
        return [_read_row(record) for record in csv.DictReader(file)]


Predicate = Callable[[dict, datetime], bool]


def association_rank(name: str) -> int:
    """The privilege of an association: owner is the highest, unknown is 0."""
    name = name.lower()
    return len(ASSOCIATIONS) - ASSOCIATIONS.index(name) if name in ASSOCIATIONS else 0


def parse_expression(text: str) -> Predicate:
    """Compile an expression such as ``prs_merged<10 and days_last < 100``.

    The text is parsed as a Python expression but never run: only the names of
    VARIABLES, whole numbers, True, False, comparisons, and, or, not and
    parentheses are accepted.
    """
    try:
        tree = ast.parse(text.strip(), mode="eval")
    except SyntaxError as error:
        raise ValueError(f"Invalid expression {text!r}: {error.msg}.") from error

    def build(node: ast.expr) -> Predicate:
        match node:
            case ast.BoolOp(op=ast.And(), values=values):
                terms = [build(v) for v in values]
                return lambda row, now: all(t(row, now) for t in terms)
            case ast.BoolOp(op=ast.Or(), values=values):
                terms = [build(v) for v in values]
                return lambda row, now: any(t(row, now) for t in terms)
            case ast.Name(id="user_bot"):
                return lambda row, now: value(row, "user_bot", now)
            case ast.UnaryOp(op=ast.Not(), operand=operand):
                inner = build(operand)
                return lambda row, now: not inner(row, now)
            case ast.Compare(left=left, ops=ops, comparators=right):
                return compare_chain(left, ops, right)
        raise ValueError(f"Not a comparison: {ast.get_source_segment(text, node)!r}.")

    def compare_chain(left, ops, right) -> Predicate:
        contains = any(isinstance(o, ast.In | ast.NotIn) for o in ops)
        terms = [term(n, contains) for n in (left, *right)]
        compares = [OPERATORS.get(type(o)) for o in ops]
        if None in compares:
            raise ValueError(f"Unsupported comparison in {text!r}.")
        kinds = {kind for kind, _, _ in terms}
        if "rank" in kinds:
            # an association is compared with associations, by privilege
            getters = [rank_getter(kind, get, literal) for kind, get, literal in terms]
        else:
            getters = [get for _, get, _ in terms]
            if len(kinds) > 1:
                raise ValueError(f"Text and numbers are compared in {text!r}.")
            allowed = TEXT_OPERATORS if "text" in kinds else NUMBER_OPERATORS
            if not all(isinstance(o, allowed) for o in ops):
                raise ValueError(
                    "Text can only be compared with ==, !=, in and not in, "
                    f"numbers not with in and not in: {text!r}."
                )
        return lambda row, now: all(
            compare(a(row, now), b(row, now))
            for compare, a, b in zip(compares, getters, getters[1:], strict=False)
        )

    def rank_getter(kind, get, literal):
        """How to get the privilege of an association or of its name."""
        if kind == "rank":
            return get
        if literal is None or literal.lower() not in ASSOCIATIONS:
            raise ValueError(
                unknown("association", literal or "?", ASSOCIATIONS) + f" (in {text!r})"
                if literal is not None
                else f"An association is compared with an association name: {text!r}."
            )
        number = association_rank(literal)
        return lambda row, now: number

    def term(node: ast.expr, as_text: bool):
        """(kind, how to get the value, the literal text if it is one)

        The kind is number, text or rank (a privilege, of the association)."""
        match node:
            case ast.Name(id="user_association" as name) if not as_text:
                return "rank", lambda row, now: association_rank(row[name]), None
            case ast.Name(id=name) if name in VARIABLES:
                kind = "text" if name in TEXT_VARIABLES else "number"
                return kind, lambda row, now: value(row, name, now), None
            case ast.Name(id=name) if name.lower() in ASSOCIATION_NAMES:
                # association_member for "member"
                literal = name.lower().removeprefix(ASSOCIATION_PREFIX)
                return "text", lambda row, now: literal, literal
            case ast.Name(id=name):
                raise ValueError(
                    unknown("variable", name, [*VARIABLES, *ASSOCIATION_NAMES])
                )
            case ast.Constant(value=str() as literal):
                return "text", lambda row, now: literal.lower(), literal
            case ast.Constant(value=bool() | int() as number):
                return "number", lambda row, now: number, None
        raise ValueError(
            f"Expected a field or a number, found "
            f"{ast.get_source_segment(text, node)!r}."
        )

    return build(tree.body)


def days_since(date: datetime | None, now: datetime) -> float:
    return float("inf") if date is None else max((now - date).days, 0)


def value(row: dict, name: str, now: datetime) -> float | bool | str:
    """The value of a variable; days_ ones are infinite if there is no data."""
    match name:
        case "user_bot":
            return is_bot(row["user_handle"])
        case "prs_closed":
            return row["prs_merged"] + row["prs_unmerged"]
        case "issues_closed":
            return row["issues_opened"] - row["issues_open"]
        case "days_first":
            return days_since(row["date_first"], now)
        case "days_last":
            return days_since(row["date_last"], now)
        case "days_to_merge":
            days = row["days_to_merge"]
            return float("inf") if days is None else days
        case "user_handle" | "user_association":
            return row[name].lower()
    return row[name]


def remove(
    rows: Iterable[dict],
    expressions: Iterable[Predicate],
    now: datetime | None = None,
) -> list[dict]:
    """Drop the rows for which any of the expressions is true."""
    now = now or datetime.now(UTC)
    expressions = list(expressions)
    return [r for r in rows if not any(e(r, now) for e in expressions)]


def keep(
    rows: Iterable[dict],
    expressions: Iterable[Predicate],
    now: datetime | None = None,
) -> list[dict]:
    """Only the rows for which all of the expressions are true."""
    now = now or datetime.now(UTC)
    expressions = list(expressions)
    return [r for r in rows if all(e(r, now) for e in expressions)]


SORT_SYNTAX = re.compile(r"([+-]?)([a-z_]+)")
# sorted ascending by default; everything else, the highest first
ASCENDING_BY_DEFAULT = ("user_handle", "days_first", "days_last", "days_to_merge")


def parse_sort(text: str) -> tuple[str, bool]:
    """(variable, descending) of [+-]variable: + ascending, - descending.

    Without a sign the handle and the days_ are ascending (the newest first),
    the rest descending (the highest first). ValueError if it is invalid."""
    match = SORT_SYNTAX.fullmatch(text.strip())
    if not match:
        raise ValueError(f"{text!r} is not +variable or -variable.")
    sign, name = match.groups()
    if name not in VARIABLES:
        raise ValueError(unknown("variable", name, VARIABLES))
    if sign:
        return name, sign == "-"
    return name, name not in ASCENDING_BY_DEFAULT


def sort_rows(
    rows: list[dict],
    sort: str = "prs_merged",
    now: datetime | None = None,
) -> list[dict]:
    """Sort by a variable, see parse_sort. Ties are sorted by handle."""
    name, descending = parse_sort(sort)
    now = now or datetime.now(UTC)

    def key(row: dict):
        if name == "user_association":
            return association_rank(row[name])  # by privilege, not by name
        return value(row, name, now)

    by_handle = sorted(rows, key=lambda r: r["user_handle"].lower())
    return sorted(by_handle, key=key, reverse=descending)


def to_csv(
    rows: Iterable[dict], columns: Iterable[str], now: datetime | None = None
) -> str:
    """The rows as CSV with the headers of the columns, as in the table.

    Only numbers and strings: the values of the variables, so that days are
    numbers (empty if unknown), True and False are 1 and 0, and there is no X/total.
    """
    now = now or datetime.now(UTC)
    columns = list(columns)
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow([COLUMN_DEFS[name][0] for name in columns])
    for row in rows:
        cells = []
        for name in columns:
            number = row[name] if name in TEXT_VARIABLES else value(row, name, now)
            if isinstance(number, float) and number == float("inf"):
                number = ""  # unknown
            cells.append(int(number) if isinstance(number, bool) else number)
        writer.writerow(["" if c is None else c for c in cells])
    return out.getvalue()
