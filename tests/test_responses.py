from datetime import timedelta

from test_cache import REPO
from typer.testing import CliRunner

from gh_community import cli
from gh_community.cache import ResponseCache
from gh_community.responses import (
    BOT,
    COLLABORATOR,
    EXTERNAL,
    bucket,
    classify,
    collect_responses,
    format_duration,
    histogram,
    render,
    summary,
)

H = timedelta(hours=1)


def pull(number, login, hour=10):
    created = f"2026-01-0{number}T{hour:02}:00:00Z"
    return {
        "number": number,
        "user": {"login": login},
        "created_at": created,
        "updated_at": created,
        "state": "open",
        "merged_at": None,
    }


def comment(number, login, association, hour):
    return {
        "user": {"login": login, "type": "User"},
        "author_association": association,
        "created_at": f"2026-01-0{number}T{hour:02}:00:00Z",
        "issue_url": f"https://api.github.com{REPO}/issues/{number}",
    }


def test_classify():
    assert classify("dependabot[bot]", "NONE") == BOT
    assert classify("copilot", "NONE") == BOT
    assert classify("someone", "NONE", bot=True) == BOT
    assert classify("x", "NONE") == EXTERNAL
    assert classify("x", "CONTRIBUTOR") == EXTERNAL
    assert classify("x", None) == EXTERNAL
    for association in ("OWNER", "MEMBER", "collaborator"):
        assert classify("x", association) == COLLABORATOR


def test_buckets_include_their_limit():
    assert bucket(timedelta(0)) == "1h"
    assert bucket(H) == "1h"
    assert bucket(H + timedelta(seconds=1)) == "3h"
    assert bucket(timedelta(days=1)) == "24h"
    assert bucket(timedelta(days=7)) == "1w"
    assert bucket(timedelta(weeks=3)) == "3w"
    assert bucket(timedelta(weeks=3, seconds=1)) == "more"


def test_histogram_counts_by_class_and_ignores_no_response():
    rows = histogram([(BOT, H), (BOT, 2 * H), (COLLABORATOR, 5 * H), None])
    counts = dict(rows)
    assert [label for label, _ in rows][:3] == ["1h", "3h", "6h"]
    assert counts["1h"] == {BOT: 1, EXTERNAL: 0, COLLABORATOR: 0}
    assert counts["3h"][BOT] == 1
    assert counts["6h"][COLLABORATOR] == 1
    assert sum(sum(c.values()) for c in counts.values()) == 3


def test_format_duration():
    assert format_duration(timedelta(minutes=45)) == "45m"
    assert format_duration(timedelta(hours=3, minutes=12)) == "3h 12m"
    assert format_duration(timedelta(hours=3)) == "3h"
    assert format_duration(timedelta(days=2, hours=4)) == "2d 4h"
    assert format_duration(timedelta(days=2)) == "2d"


def test_summary_has_average_and_median_per_class():
    lines = summary([(BOT, H), (BOT, 5 * H), (EXTERNAL, 2 * H), None])
    assert lines == [
        (BOT, 2, "average 3h, median 3h"),
        (EXTERNAL, 1, "average 2h, median 2h"),
    ]


def test_render():
    text = "\n".join(render("Issues", [(BOT, H), (COLLABORATOR, 20 * H), None]))
    assert text.startswith("Issues (3, 1 without response)")
    assert "<= 1h | █ 1 0 0" in text
    assert "<= 24h | █ 0 0 1" in text.replace("█" * 1 + " ", "█ ")  # one bar
    assert "> 3w" in text
    assert "bot: 1 responses, average 1h, median 1h" in text
    assert render("Issues", [None]) == [
        "Issues (1, 1 without response)",
        "  no responses",
    ]


def test_render_scales_long_bars():
    lines = render("PRs", [(BOT, H)] * 100)
    assert "one bar character is up to 3 responses" in "\n".join(lines)
    assert any("| " + "█" * 34 + " 100 0 0" in line for line in lines)


def serve(api):
    """PR 1: a bot after 1h, then a collaborator; PR 2: the author, then an
    external review after 30h; PR 3: no response. Issue 4: a collaborator after
    2h, the author comments before; issue 5: nothing."""
    api.data[f"{REPO}/pulls"] = [pull(1, "ann"), pull(2, "ben"), pull(3, "cat")]
    api.data[f"{REPO}/issues"] = [
        *({**p, "pull_request": {}} for p in api.data[f"{REPO}/pulls"]),
        pull(4, "dan"),
        pull(5, "eve"),
    ]
    api.data[f"{REPO}/issues/comments"] = [
        comment(1, "ci[bot]", "NONE", 11),
        comment(1, "maint", "MEMBER", 12),
        comment(2, "ben", "CONTRIBUTOR", 11),  # the author
        comment(4, "dan", "NONE", 10),  # the author
        comment(4, "maint", "OWNER", 12),
    ]
    api.data[f"{REPO}/pulls/comments"] = []
    for number in (1, 3, 4):
        api.data[f"{REPO}/pulls/{number}/reviews"] = []
    api.data[f"{REPO}/pulls/2/reviews"] = [
        {
            "user": {"login": "stranger", "type": "User"},
            "author_association": "NONE",
            "state": "COMMENTED",
            "submitted_at": "2026-01-03T16:00:00Z",
        },
        {
            "user": {"login": "maint", "type": "User"},
            "author_association": "MEMBER",
            "state": "PENDING",
            "submitted_at": None,
        },
    ]


def collect(api, cache=None):
    messages = []
    found = collect_responses(
        "t", ["a/b"], messages.append, cache=cache, base_url=api.url
    )
    return found, messages


def test_first_response_of_pull_requests_and_issues(api):
    serve(api)
    found, _ = collect(api)
    assert found["prs"] == [(BOT, H), (EXTERNAL, 30 * H), None]
    assert found["issues"] == [(COLLABORATOR, 2 * H), None]


def test_second_run_uses_no_api_calls(api, tmp_path):
    serve(api)
    first, _ = collect(api, ResponseCache(tmp_path))
    used = api.used
    assert used > 0
    api.log.clear()
    second, _ = collect(api, ResponseCache(tmp_path))
    assert second == first
    assert api.used == used
    assert api.requests(status=200) == []


def test_command_shows_both_charts(api, tmp_path, monkeypatch):
    serve(api)
    monkeypatch.setattr(cli, "default_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(cli, "collect_responses", lambda *a, **k: collect(api)[0])
    result = CliRunner().invoke(cli.app, ["response", "a/b", "--token", "t"])
    assert result.exit_code == 0, result.output
    assert "Pull requests (3, 1 without response)" in result.stdout
    assert "Issues (2, 1 without response)" in result.stdout
    assert result.stdout.index("Pull requests") < result.stdout.index("Issues")
