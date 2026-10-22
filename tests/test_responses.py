import json
import threading
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from typer.testing import CliRunner

from gh_community import cli, responses
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
    table,
)

H = timedelta(hours=1)


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


def test_histogram_counts_each_class_and_ignores_no_response():
    rows = histogram([{BOT: H}, {BOT: 2 * H, COLLABORATOR: 5 * H}, {}])
    counts = dict(rows)
    assert [label for label, _ in rows][:3] == ["1h", "3h", "6h"]
    assert counts["1h"] == {BOT: 1, EXTERNAL: 0, COLLABORATOR: 0}
    assert counts["3h"][BOT] == 1
    assert counts["6h"][COLLABORATOR] == 1
    assert sum(sum(c.values()) for c in counts.values()) == 3


def test_format_duration():
    assert format_duration(timedelta(minutes=45)) == "45min"
    assert format_duration(timedelta(hours=3, minutes=12)) == "3h 12min"
    assert format_duration(timedelta(hours=3)) == "3h"
    assert format_duration(timedelta(days=2, hours=4)) == "2d 4h"
    assert format_duration(timedelta(days=2)) == "2d"


def test_summary_rows_measured_normal_and_exponential():
    rows = summary([{BOT: H}, {BOT: 5 * H, EXTERNAL: 2 * H}, {}])
    assert rows == [
        (BOT, "2", "measured", "3h", "2h", "3h", "-"),
        (BOT, "2", "normal", "3h", "2h", "3h", "7h 39min"),
        (BOT, "2", "exponential", "3h", "2h 7min", "2h 5min", "8h 59min"),
        (EXTERNAL, "1", "measured", "2h", "-", "2h", "-"),
        (EXTERNAL, "1", "normal", "2h", "-", "2h", "-"),
        (EXTERNAL, "1", "exponential", "2h", "2h", "1h 23min", "5h 59min"),
    ]


def test_table_is_aligned():
    rows = summary([{BOT: H}, {BOT: 5 * H}, {COLLABORATOR: 20 * H}])
    lines = [line for _, line in table(rows)]
    assert lines[0].split() == [
        "class",
        "n",
        "fit",
        "average",
        "std",
        "error",
        "median",
        "95%",
    ]
    assert len({len(line) for line in lines}) == 1  # the same width
    assert lines[1].split()[:3] == ["bot", "2", "measured"]
    assert lines[3].endswith("8h 59min")
    assert [c for c, _ in table(rows)][:2] == ["", BOT]


def test_render():
    entries = [{BOT: H, COLLABORATOR: 20 * H}, {COLLABORATOR: 2 * H}, {}]
    lines = render("Issues", entries)
    text = "\n".join(lines)
    assert lines[0] == "Issues (3, 1 without any response)"
    assert lines[1] == "  █ bot  █ external  █ collaborator or higher"
    # the numbers by the time, right aligned, then the stacked bars
    assert "   <= 1h  1 0 0 | █" in lines
    assert "   <= 3h  0 0 1 | █" in lines
    assert "  <= 24h  0 0 1 | █" in lines  # the slower collaborator counts
    assert "   <= 2w  0 0 0 | " in lines
    assert "exponential" in text and "std error" in text
    assert render("Issues", [{}]) == [
        "Issues (1, 1 without any response)",
        "  no responses",
    ]


def test_render_stacks_the_classes_and_aligns_numbers():
    entries = [{BOT: H, EXTERNAL: H, COLLABORATOR: H}] + [{BOT: H}] * 11
    line = next(x for x in render("PRs", entries) if "<= 1h" in x)
    assert line == "   <= 1h  12  1  1 | " + "█" * 14
    assert "   <= 3h   0  0  0 | " in "\n".join(render("PRs", entries))


def test_render_scales_long_bars():
    lines = render("PRs", [{BOT: H}] * 100)
    assert "one bar character is up to 3 responses" in "\n".join(lines)
    assert any(line.endswith("100   0   0 | " + "█" * 34) for line in lines)


class FakeGraphQL(ThreadingHTTPServer):
    """Answers the queries of gh_community.responses from nodes in memory."""

    def __init__(self):
        super().__init__(("127.0.0.1", 0), Handler)
        self.items = {"pullRequests": [], "issues": []}
        self.used = 0
        self.queries = []  # (field read or "more", after)

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server_port}"


def trimmed(node, inner):
    """The node with only the first inner comments and reviews."""
    out = dict(node)
    for field in ("comments", "reviews"):
        if field in node:
            out[field] = connection(node[field], 0, inner)
    return out


def connection(nodes, start, inner):
    chunk = nodes[start : start + inner]
    end = start + len(chunk)
    page = {"hasNextPage": end < len(nodes), "endCursor": str(end)}
    return {"nodes": chunk, "pageInfo": page}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):  # the rate limit, asked before the first request
        body = {"resources": {"core": {"limit": 5000, "remaining": 5000}}}
        out = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def do_POST(self):
        server = self.server
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        query, variables = body["query"], body["variables"]
        server.used += 1
        if "node(id" in query:
            field = "reviews" if "reviews(" in query else "comments"
            node = next(
                n
                for items in server.items.values()
                for n in items
                if n["id"] == variables["id"]
            )
            server.queries.append(("more", variables["after"]))
            start = int(variables["after"])
            data = {"node": {field: connection(node[field], start, variables["inner"])}}
        else:
            field = "pullRequests" if "pullRequests(" in query else "issues"
            server.queries.append((field, variables["after"]))
            ordered = sorted(
                server.items[field], key=lambda n: n["updatedAt"], reverse=True
            )
            start = int(variables["after"] or 0)
            chunk = ordered[start : start + variables["page"]]
            nodes = [trimmed(n, variables["inner"]) for n in chunk]
            end = start + len(chunk)
            page = {"hasNextPage": end < len(ordered), "endCursor": str(end)}
            total = len(ordered)
            data = {
                "repository": {
                    field: {"totalCount": total, "nodes": nodes, "pageInfo": page}
                }
            }
        out = json.dumps({"data": data}).encode()
        self.send_response(200)
        self.send_header("X-RateLimit-Limit", "5000")
        self.send_header("X-RateLimit-Remaining", str(5000 - server.used))
        self.send_header("X-RateLimit-Reset", "1800000000")
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)


@pytest.fixture
def graphql(monkeypatch):
    monkeypatch.setattr(responses, "PAGE", 2)
    monkeypatch.setattr(responses, "INNER", 2)
    monkeypatch.setattr(responses, "FOLLOW", 2)
    monkeypatch.setattr(responses, "REQUEST_DELAY", 0)
    server = FakeGraphQL()
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server
    server.shutdown()
    server.server_close()


def actor(login, kind="User"):
    return {"login": login, "__typename": kind}


def item(number, login, updated=None, comments=(), reviews=None):
    """comments and reviews are (login, association, hour) of 2026-01-0N."""
    day = f"2026-01-0{number}"
    node = {
        "id": f"id{number}",
        "number": number,
        "createdAt": f"{day}T10:00:00Z",
        "updatedAt": updated or f"{day}T23:00:00Z",
        "author": {"login": login},
        "comments": [
            {
                "createdAt": f"{day}T{hour:02}:00:00Z",
                "author": actor(who, "Bot" if who == "robot" else "User"),
                "authorAssociation": association,
            }
            for who, association, hour in comments
        ],
    }
    if reviews is not None:
        node["reviews"] = [
            {
                "submittedAt": f"{day}T{hour:02}:00:00Z",
                "author": actor(who),
                "authorAssociation": association,
            }
            for who, association, hour in reviews
        ]
    return node


def serve(graphql):
    """PR 1: a bot after 1h, then a collaborator after 2h; PR 2: the author, then
    an external review after 30h (the day after); PR 3: no response. Issue 4: the
    author comments before a collaborator, 2h after, with more comments than
    come with the item; issue 5: nothing; issue 6: two bots, then a collaborator
    after 5h on the next page."""
    graphql.items["pullRequests"] = [
        item(
            1,
            "ann",
            comments=[("robot", "NONE", 11), ("maint", "MEMBER", 12)],
            reviews=[],
        ),
        item(
            2,
            "Ben",  # handles are not case sensitive: "ben" is the author
            comments=[("ben", "CONTRIBUTOR", 11)],
            reviews=[("stranger", "NONE", 16)],
        ),
        item(3, "cat", reviews=[]),
    ]
    graphql.items["pullRequests"][1]["reviews"][0]["submittedAt"] = (
        "2026-01-03T16:00:00Z"
    )
    graphql.items["issues"] = [
        item(
            4,
            "dan",
            comments=[("dan", "NONE", 10), ("dan", "NONE", 11), ("maint", "OWNER", 12)],
        ),
        item(5, "eve"),
        item(
            6,
            "fay",
            comments=[
                ("robot", "NONE", 11),
                ("robot", "NONE", 12),
                ("maint", "MEMBER", 15),
            ],
        ),
    ]


def unordered(entries):
    """The order is the one of the changes, not of the numbers."""
    return sorted(entries, key=lambda e: sorted(e.items()))


def pages(graphql):
    """The queries for pages of items, not for more comments of one."""
    return [q for q in graphql.queries if q[0] != "more"]


def collect(graphql, cache=None, since=None):
    messages = []
    found = collect_responses(
        "t", ["a/b"], messages.append, cache=cache, base_url=graphql.url, since=since
    )
    return found, messages


def test_first_response_of_pull_requests_and_issues(graphql):
    serve(graphql)
    found, _ = collect(graphql)
    assert unordered(found["prs"]) == unordered(
        [{BOT: H, COLLABORATOR: 2 * H}, {EXTERNAL: 30 * H}, {}]
    )
    assert unordered(found["issues"]) == unordered(
        [{COLLABORATOR: 2 * H}, {}, {BOT: H, COLLABORATOR: 5 * H}]
    )


def test_progress_tells_how_many_of_all_are_read(graphql, tmp_path):
    serve(graphql)
    _, messages = collect(graphql, ResponseCache(tmp_path))
    assert any("pull requests 2/3 read" in m for m in messages)
    assert any("pull requests 3/3 read" in m for m in messages)
    _, messages = collect(graphql, ResponseCache(tmp_path))
    assert any("pull requests 1/3 read, the rest unchanged" in m for m in messages)


def test_a_faster_bot_does_not_hide_the_others(graphql):
    """Issue 6 has two bot comments first, the collaborator is on the next page."""
    serve(graphql)
    found, _ = collect(graphql)
    assert {BOT: H, COLLABORATOR: 5 * H} in found["issues"]
    assert ("more", "2") in graphql.queries


def test_pages_are_read_while_a_class_is_missing(graphql):
    """Issue 4: the author comments twice, the collaborator is on the next page,
    and there is nothing more to read afterwards (no bot, no external)."""
    serve(graphql)
    collect(graphql)
    assert [q for q in graphql.queries if q[0] == "more"].count(("more", "2")) == 2


def test_second_run_reads_only_the_newest_items(graphql, tmp_path):
    serve(graphql)
    first, _ = collect(graphql, ResponseCache(tmp_path))
    graphql.queries.clear()
    second, messages = collect(graphql, ResponseCache(tmp_path))
    assert unordered(second["prs"]) == unordered(first["prs"])
    assert unordered(second["issues"]) == unordered(first["issues"])
    # one request per kind: the newest item is read again, the next is older
    assert pages(graphql) == [("pullRequests", None), ("issues", None)]
    assert "unchanged, not requested" in "\n".join(messages)


def test_changed_items_are_read_again(graphql, tmp_path):
    serve(graphql)
    collect(graphql, ResponseCache(tmp_path))
    graphql.queries.clear()
    pull = graphql.items["pullRequests"][2]  # PR 3 gets a comment by a member
    pull["comments"] = [
        {
            "createdAt": "2026-01-03T13:00:00Z",
            "author": actor("maint"),
            "authorAssociation": "OWNER",
        }
    ]
    pull["updatedAt"] = "2026-02-01T00:00:00Z"
    found, _ = collect(graphql, ResponseCache(tmp_path))
    assert unordered(found["prs"]) == unordered(
        [{BOT: H, COLLABORATOR: 2 * H}, {EXTERNAL: 30 * H}, {COLLABORATOR: 3 * H}]
    )
    assert pages(graphql) == [("pullRequests", None), ("issues", None)]


def test_without_cache_everything_is_read_each_time(graphql):
    serve(graphql)
    collect(graphql)
    graphql.queries.clear()
    collect(graphql)
    assert graphql.queries.count(("pullRequests", None)) == 1
    assert ("pullRequests", "2") in graphql.queries


def test_command_shows_both_charts(graphql, tmp_path, monkeypatch):
    serve(graphql)
    monkeypatch.setattr(cli, "default_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(cli, "collect_responses", lambda *a, **k: collect(graphql)[0])
    result = CliRunner().invoke(cli.app, ["response", "a/b", "--token", "t"])
    assert result.exit_code == 0, result.output
    assert "Pull requests (3, 1 without any response)" in result.stdout
    assert "Issues (3, 1 without any response)" in result.stdout
    assert result.stdout.index("Pull requests") < result.stdout.index("Issues")


def test_since_includes_only_items_created_since(graphql):
    serve(graphql)
    found, messages = collect(graphql, since=date(2026, 1, 3))
    assert found["prs"] == [{}]  # PR 3
    assert unordered(found["issues"]) == unordered(
        [{COLLABORATOR: 2 * H}, {}, {BOT: H, COLLABORATOR: 5 * H}]
    )
    # the older pull requests are not even read (page size 2: PR 3, PR 2)
    assert ("pullRequests", "2") not in graphql.queries
    assert any("the rest older" in m for m in messages)


def test_since_with_cache(graphql, tmp_path):
    serve(graphql)
    collect(graphql, ResponseCache(tmp_path), since=date(2026, 1, 3))
    graphql.queries.clear()
    # the same or a later date is answered from what was read
    found, _ = collect(graphql, ResponseCache(tmp_path), since=date(2026, 1, 4))
    assert len(found["issues"]) == 3
    assert pages(graphql) == [("pullRequests", None), ("issues", None)]
    # an earlier date needs more: everything is read again
    found, _ = collect(graphql, ResponseCache(tmp_path), since=date(2026, 1, 1))
    assert len(found["prs"]) == 3
    assert ("pullRequests", "2") in graphql.queries
    # and without a date, too, then a date again needs nothing more
    found, _ = collect(graphql, ResponseCache(tmp_path))
    graphql.queries.clear()
    found, _ = collect(graphql, ResponseCache(tmp_path), since=date(2026, 1, 2))
    assert len(found["prs"]) == 2
    assert pages(graphql) == [("pullRequests", None), ("issues", None)]


def test_command_checks_the_date(graphql, tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "default_cache_dir", lambda: tmp_path)
    result = CliRunner().invoke(
        cli.app, ["response", "a/b", "--token", "t", "--since", "yesterday"]
    )
    assert result.exit_code == 2
    assert "--since" in result.output
