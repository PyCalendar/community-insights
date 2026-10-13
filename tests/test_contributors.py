from datetime import UTC, datetime

from gh_community.contributors import days_ago, last_page, sort_rows, to_markdown


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
    return {
        "handle": handle, "commits": commits, "prs": prs, "merged": merged,
        "opened": opened, "commented": commented, "pr_commented": pr_commented,
        "reviewed": reviewed, "activity": activity,
    }  # fmt: skip


ROWS = [
    row("bob", 5, 120, 4, 2, 0, 3, 9, datetime(2026, 2, 1, 12, tzinfo=UTC)),
    row("alexander", 1200, 3, 1, 0, 14, 0, 0, datetime(2026, 3, 1, tzinfo=UTC)),
    row("carol", 5, 7, 7, 10, 1, 25, 100, None),
]


def order(column):
    return [r["handle"] for r in sort_rows(ROWS, column)]


def test_sort_default_is_merged_prs():
    assert [r["handle"] for r in sort_rows(ROWS)] == ["carol", "bob", "alexander"]


def test_sort_prs_sorts_by_merged_only():
    assert order("prs") == ["carol", "bob", "alexander"]
    rows = [row("b", prs=1, merged=2), row("a", prs=99, merged=2)]
    assert [r["handle"] for r in sort_rows(rows, "prs")] == ["a", "b"]


def test_sort_commits_and_handle():
    assert order("commits") == ["alexander", "bob", "carol"]
    assert order("handle") == ["alexander", "bob", "carol"]


def test_sort_issue_and_review_columns():
    assert order("opened") == ["carol", "bob", "alexander"]
    assert order("commented") == ["alexander", "carol", "bob"]
    assert order("pr_commented") == ["carol", "bob", "alexander"]
    assert order("reviewed") == ["carol", "bob", "alexander"]


def test_sort_activity_newest_first_unknown_last():
    assert order("activity") == ["alexander", "bob", "carol"]


def test_markdown_alignment():
    now = datetime(2026, 3, 11, 8, tzinfo=UTC)
    assert to_markdown(sort_rows(ROWS), now) == "\n".join(
        [
            "| handle    | commits |   prs | issues opened | issues commented on "
            "| PRs commented on | PRs reviewed | last activity |",
            "| --------- | ------: | ----: | ------------: | ------------------: "
            "| ---------------: | -----------: | ------------: |",
            "| carol     |       5 |   7/7 |            10 |                   1 "
            "|               25 |          100 |             - |",
            "| bob       |       5 | 4/120 |             2 |                   0 "
            "|                3 |            9 |   37 days ago |",
            "| alexander |    1200 |   1/3 |             0 |                  14 "
            "|                0 |            0 |   10 days ago |",
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
    assert days_ago(datetime(2026, 3, 10, 8, tzinfo=UTC), now) == "1 day ago"
    assert days_ago(datetime(2026, 1, 1, tzinfo=UTC), now) == "69 days ago"
    assert days_ago(datetime(2026, 3, 12, tzinfo=UTC), now) == "today"  # clock skew
