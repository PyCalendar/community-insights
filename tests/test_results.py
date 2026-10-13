from datetime import UTC, datetime, timedelta

import pytest
from rows import blank

from gh_community.results import (
    parse_expression,
    read_result,
    remove,
    to_csv,
    write_result,
)

NOW = datetime(2026, 10, 13, tzinfo=UTC)


def row(
    handle, merged=0, total=None, opened=0, days=None, prs_open=0, unmerged=0, **more
):
    return blank(
        user_handle=handle, prs_merged=merged, prs_open=prs_open,
        prs_unmerged=unmerged, issues_opened=opened,
        prs_total=merged + prs_open + unmerged if total is None else total,
        date_last=None if days is None else NOW - timedelta(days=days), **more,
    )  # fmt: skip


def kept(rows, *expressions):
    result = remove(rows, [parse_expression(e) for e in expressions], NOW)
    return [r["user_handle"] for r in result]


def test_grammar_precedence_and_parentheses():
    rows = [row("a", merged=5, days=50), row("b", merged=5, days=200, opened=1),
            row("c", merged=5, days=200), row("d", merged=20, days=50)]  # fmt: skip
    expression = (
        "prs_total>=0 and prs_merged<10 and (days_last < 100 or issues_opened > 0)"
    )
    assert kept(rows, expression) == ["c", "d"]
    # and binds tighter than or
    assert kept(rows, "prs_merged > 10 or days_last < 100 and issues_opened == 1") == [
        "a",
        "b",
        "c",
    ]
    assert kept(rows, "not prs_merged < 10") == ["a", "b", "c"]


def test_no_activity_is_infinitely_old():
    assert kept([row("a")], "days_last > 1000") == []


@pytest.mark.parametrize(
    "text",
    [
        "",
        "prs_merged",
        "prs_merged <",
        "x < 1",
        "merged < 1",  # the old name
        "prs_merged < a",
        "(prs_merged < 1",
        "prs_merged < 1)",
        "__import__('os')",
        "prs_merged < 1.5",
        "days_last",
        "prs_merged in 3",
        "user_handle > 'a'",
        "user_association == 1",
        "'a' in 'b' < 3",
    ],
)
def test_invalid_expressions(text):
    with pytest.raises(ValueError):
        parse_expression(text)


def test_csv_roundtrip(tmp_path):
    rows = [row("a", merged=1, unmerged=1, days=3), row("b")]
    write_result(tmp_path / "r.csv", rows)
    assert read_result(tmp_path / "r.csv") == rows


def test_bot_variable():
    rows = [row("alice"), row("dependabot[bot]"), row("Copilot")]
    # kept: the rows that remain after removing the matching ones
    assert kept(rows, "user_bot") == ["alice"]
    assert kept(rows, "not user_bot") == ["dependabot[bot]", "Copilot"]
    assert kept(rows, "user_bot == True") == ["alice"]
    assert kept(rows, "prs_merged < 1 and not user_bot") == [
        "dependabot[bot]",
        "Copilot",
    ]


def test_pull_request_states(tmp_path):
    rows = [row("a", merged=2, prs_open=1, unmerged=2)]
    write_result(tmp_path / "r.csv", rows)
    header, line = (tmp_path / "r.csv").read_text().splitlines()
    # what can be calculated is not stored
    columns = header.split(",")
    assert columns[:6] == (
        "user_handle user_association commits_total prs_open prs_merged "
        "prs_unmerged".split()
    )
    assert not {"prs_total", "prs_closed", "issues_closed"} & set(columns)
    assert read_result(tmp_path / "r.csv") == rows
    assert rows[0]["prs_total"] == 5
    assert kept(rows, "prs_total == 5 and prs_closed == 4 and prs_open == 1") == []
    assert kept(rows, "prs_closed > 4 or prs_total < 5") == ["a"]


def test_old_file_with_the_old_names(tmp_path):
    (tmp_path / "old.csv").write_text(
        "handle,commits,prs,merged,opened,commented,pr_commented,reviewed,activity\n"
        "a,1,3,2,0,0,0,0,\n"
        "b,1,3,2,0,0,0,0,2026-01-01T10:00:00+00:00\n"
    )
    old, other = read_result(tmp_path / "old.csv")
    assert (old["user_handle"], old["commits_total"]) == ("a", 1)
    assert (old["prs_total"], old["prs_merged"]) == (3, 2)
    assert (old["prs_open"], old["prs_unmerged"]) == (0, 0)
    assert old["date_last"] is None and other["date_last"].year == 2026


def test_text_and_dates_in_expressions():
    rows = [
        row("a", user_association="owner", date_first=NOW - timedelta(days=400)),
        row("b", user_association="none", date_first=NOW - timedelta(days=3)),
        row("c"),
    ]
    assert kept(rows, "user_association == 'owner'") == ["b", "c"]
    assert kept(rows, "user_association != 'owner' and days_first < 10") == ["a", "c"]
    assert kept(rows, "days_first > 365") == ["b"]  # unknown is infinite


def test_text_contains():
    rows = [row("alice"), row("dependabot[bot]"), row("Bob", user_association="none")]
    assert kept(rows, "'[BOT]' in user_handle") == ["alice", "Bob"]
    assert kept(rows, "'[bot]' not in user_handle") == ["dependabot[bot]"]
    # an unknown (empty) association is part of any text
    assert kept(rows, "user_association in 'owner member'") == ["Bob"]
    assert kept(rows, "user_handle in 'alice bob'") == ["dependabot[bot]"]


def test_more_variables():
    rows = [
        row("a", opened=5, issues_open=2, days_to_merge=1.5, actions_merges=3),
        row("b", opened=5, issues_open=2),
    ]
    assert kept(rows, "issues_closed == 3 and days_to_merge < 2") == ["b"]
    assert kept(rows, "actions_merges >= 3 and actions_labels == 0") == ["b"]


def test_association_is_always_lowercase(tmp_path):
    (tmp_path / "old.csv").write_text(
        "user_handle,user_association\na,MEMBER\nb,First_Time_Contributor\n"
    )
    old, other = read_result(tmp_path / "old.csv")
    assert (old["user_association"], other["user_association"]) == (
        "member",
        "first_time_contributor",
    )
    assert kept([old], "user_association in 'owner member'") == []
    assert kept([old], "user_association == 'MEMBER'") == []


def test_association_is_ordered_by_privilege():
    rows = [
        row("o", user_association="owner"),
        row("m", user_association="member"),
        row("c", user_association="contributor"),
        row("n", user_association="none"),
        row("u"),  # unknown
    ]
    # kept: the rows that remain after removing the matching ones
    assert kept(rows, "user_association > association_member") == ["m", "c", "n", "u"]
    assert kept(rows, "user_association >= 'member'") == ["c", "n", "u"]
    assert kept(rows, "user_association < association_contributor") == ["o", "m", "c"]
    assert kept(rows, "'member' <= user_association") == ["c", "n", "u"]
    both = "association_contributor < user_association <= association_member"
    assert kept(rows, both) == ["o", "c", "n", "u"]
    assert kept(
        rows, "user_association == ASSOCIATION_MEMBER or user_association == 'None'"
    ) == [
        "o",
        "c",
        "u",
    ]
    assert kept(rows, "user_association >= 'MEMBER'") == ["c", "n", "u"]


@pytest.mark.parametrize(
    "text",
    [
        "user_association > 'nobody'",
        "user_association > 3",
        "user_association > user_handle",
    ],
)
def test_invalid_association_comparisons(text):
    with pytest.raises(ValueError):
        parse_expression(text)


def error(text):
    with pytest.raises(ValueError) as caught:
        parse_expression(text)
    return str(caught.value)


def test_unknown_names_suggest_the_closest():
    assert "Did you mean 'prs_merged'" in error("prs_mrged > 3")
    assert "'prs_open' or 'issues_open'" in error("open > 3")  # contained
    assert "Did you mean 'association_member'" in error(
        "user_association > association_membr"
    )
    message = error("zzzzz > 1")
    assert "Did you mean" not in message
    listed = message.split("Use one of: ")[1].rstrip(".").split(", ")
    assert listed == sorted(listed)


def test_bare_association_names_need_the_prefix():
    rows = [row("m", user_association="member")]
    assert kept(rows, "user_association == association_member") == []
    assert kept(rows, "user_association == 'member'") == []
    for text in ("user_association == member", "user_association > owner",
                 "user_association > none"):  # fmt: skip
        assert "Unknown variable" in error(text)
    assert "Did you mean 'association_member'" in error(
        "user_association > association_memer"
    )


def test_csv_has_only_numbers_and_strings():
    rows = [
        row("Alice", merged=2, total=5, opened=4, days=3, user_association="member"),
        row("dependabot[bot]"),
    ]
    rows[0]["issues_open"] = 1
    rows[0]["days_to_merge"] = 1.5
    columns = [
        "user_handle", "user_association", "user_bot", "prs_merged", "prs_total",
        "issues_closed", "days_last", "days_to_merge",
    ]  # fmt: skip
    assert to_csv(rows, columns, NOW) == (
        "handle,association,bot,merged PRs,PRs,closed issues,"
        "last activity,days to merge\n"
        "Alice,member,0,2,5,3,3,1.5\n"
        "dependabot[bot],,1,0,0,0,,\n"
    )
