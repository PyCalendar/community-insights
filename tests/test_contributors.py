from datetime import UTC, datetime

import pytest
from rows import blank

from gh_community.contributors import (
    DEFAULT_COLUMNS,
    days_ago,
    last_page,
    parse_columns,
    to_markdown,
)
from gh_community.results import sort_rows


def row(
    handle,
    commits=0,
    prs=0,
    merged=0,
    opened=0,
    commented=0,
    pr_commented=0,
    reviewed=0,
    activity=None,
):
    return blank(
        user_handle=handle, commits_total=commits, prs_total=prs, prs_merged=merged,
        issues_opened=opened, issues_commented=commented,
        prs_commented=pr_commented, prs_reviewed=reviewed, date_last=activity,
    )  # fmt: skip


ROWS = [
    row("bob", 5, 120, 4, 2, 0, 3, 9, datetime(2026, 2, 1, 12, tzinfo=UTC)),
    row("alexander", 1200, 3, 1, 0, 14, 0, 0, datetime(2026, 3, 1, tzinfo=UTC)),
    row("carol", 5, 7, 7, 10, 1, 25, 100, None),
]


def order(column):
    return [r["user_handle"] for r in sort_rows(ROWS, column)]


def test_sort_default_is_merged_prs():
    assert [r["user_handle"] for r in sort_rows(ROWS)] == ["carol", "bob", "alexander"]


def test_sort_prs_merged_not_total():
    assert order("prs_merged") == ["carol", "bob", "alexander"]
    rows = [row("b", prs=1, merged=2), row("a", prs=99, merged=2)]
    assert [r["user_handle"] for r in sort_rows(rows, "prs_merged")] == ["a", "b"]


def test_sort_commits_and_handle():
    assert order("commits_total") == ["alexander", "bob", "carol"]
    assert order("user_handle") == ["alexander", "bob", "carol"]


def test_sort_issue_and_review_columns():
    assert order("issues_opened") == ["carol", "bob", "alexander"]
    assert order("issues_commented") == ["alexander", "carol", "bob"]
    assert order("prs_commented") == ["carol", "bob", "alexander"]
    assert order("prs_reviewed") == ["carol", "bob", "alexander"]


def test_sort_days_last_newest_first_unknown_last():
    assert order("days_last") == ["alexander", "bob", "carol"]


def test_markdown_alignment():
    now = datetime(2026, 3, 11, 8, tzinfo=UTC)
    assert to_markdown(sort_rows(ROWS), now) == "\n".join(
        [
            "| handle    | commits | merged PRs | issues opened | issues commented on "
            "| PRs commented on | PRs reviewed | last activity |",
            "| --------- | ------: | ---------: | ------------: | ------------------: "
            "| ---------------: | -----------: | ------------: |",
            "| carol     |       5 |        7/7 |            10 |                   1 "
            "|               25 |          100 |             - |",
            "| bob       |       5 |      4/120 |             2 |                   0 "
            "|                3 |            9 |       37 days |",
            "| alexander |    1200 |        1/3 |             0 |                  14 "
            "|                0 |            0 |       10 days |",
        ]
    )


def test_last_page():
    link = (
        '<https://x/r?per_page=2&page=2>; rel="next", '
        '<https://x/r?per_page=2&page=7>; rel="last"'
    )
    assert last_page(link) == 7
    assert last_page(None) is None


def test_days_ago():
    now = datetime(2026, 3, 11, 8, tzinfo=UTC)
    assert days_ago(None, now) == "-"
    assert days_ago(datetime(2026, 3, 11, 1, tzinfo=UTC), now) == "today"
    assert days_ago(datetime(2026, 3, 10, 9, tzinfo=UTC), now) == "today"
    assert days_ago(datetime(2026, 3, 10, 8, tzinfo=UTC), now) == "1 day "
    assert days_ago(datetime(2026, 1, 1, tzinfo=UTC), now) == "69 days"
    assert days_ago(datetime(2026, 3, 12, tzinfo=UTC), now) == "today"  # clock skew


def test_columns_specification():
    assert parse_columns("user_handle+prs_merged") == ["user_handle", "prs_merged"]
    assert parse_columns("commits_total") == ["commits_total"]
    assert parse_columns("+prs_open") == [*DEFAULT_COLUMNS, "prs_open"]
    assert parse_columns("-days_last-commits_total+prs_open") == [
        "user_handle",
        "prs_merged",
        "issues_opened",
        "issues_commented",
        "prs_commented",
        "prs_reviewed",
        "prs_open",
    ]
    # adding what is shown or removing what is not shown changes nothing
    assert parse_columns("+commits_total-prs_open") == list(DEFAULT_COLUMNS)


@pytest.mark.parametrize(
    "text",
    ["", "+", "a,b", "+commits_total,days_last", "+nope", "x y", "+-x", "a++b", "A"],
)
def test_invalid_columns_specification(text):
    with pytest.raises(ValueError):
        parse_columns(text)


def test_all_columns_removed():
    with pytest.raises(ValueError):
        parse_columns("user_handle-user_handle")


def test_unknown_column_suggests_the_closest():
    with pytest.raises(ValueError, match="Did you mean 'prs_open'"):
        parse_columns("+prs_opn")


def test_sort_direction_with_sign():
    # ascending days_last: the newest activity first, unknown (infinite) last
    assert order("+days_last") == ["alexander", "bob", "carol"]
    assert order("days_last") == order("+days_last")
    assert order("-days_last") == ["carol", "bob", "alexander"]
    assert order("+commits_total") == ["bob", "carol", "alexander"]  # ties: handle
    assert order("-commits_total") == ["alexander", "bob", "carol"]
    assert order("-user_handle") == ["carol", "bob", "alexander"]
    assert order("+issues_closed") == ["alexander", "bob", "carol"]


def test_sort_association_by_privilege_and_errors():
    rows = [
        row("a"), row("b"), row("c"),
    ]  # fmt: skip
    rows[0]["user_association"] = "member"
    rows[1]["user_association"] = "owner"
    rows[2]["user_association"] = "none"
    assert [r["user_handle"] for r in sort_rows(rows, "user_association")] == [
        "b",
        "a",
        "c",
    ]
    with pytest.raises(ValueError, match="Did you mean 'prs_merged'"):
        sort_rows(rows, "-prs_mrged")
    with pytest.raises(ValueError):
        sort_rows(rows, "+-days_last")
