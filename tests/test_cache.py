"""Collecting and caching, tested with PyGithub against a local fake GitHub API."""

import hashlib
import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import pytest

from gh_community import contributors
from gh_community.cache import ResponseCache

PER_PAGE = 2
REPO = "/repos/a/b"


def user(login):
    return {"login": login}


def pull(number, login, created, merged):
    return {
        "number": number,
        "user": user(login),
        "created_at": f"{created}T10:00:00Z",
        "updated_at": f"{created}T12:00:00Z",
        "merged_at": f"{created}T11:00:00Z" if merged else None,
    }


def issue(number, login, created):
    return {"number": number, "user": user(login), "created_at": f"{created}T10:00:00Z"}


def issue_comment(number, login, created):
    return {
        "user": user(login),
        "created_at": f"{created}T10:00:00Z",
        "issue_url": f"https://api.github.com{REPO}/issues/{number}",
    }


def review_comment(number, login, created):
    return {
        "user": user(login),
        "created_at": f"{created}T10:00:00Z",
        "pull_request_url": f"https://api.github.com{REPO}/pulls/{number}",
    }


def review(login, state, submitted):
    return {
        "user": user(login),
        "state": state,
        "submitted_at": f"{submitted}T10:00:00Z",
    }


def make_data():
    pulls = [
        pull(1, "alice", "2026-01-01", True),
        pull(2, "bob", "2026-01-02", False),
        pull(3, "alice", "2026-01-03", True),
        pull(4, "carol", "2026-01-04", True),
    ]
    issues = [  # the issues endpoint lists pull requests, too
        *({**p, "pull_request": {}} for p in pulls),
        issue(5, "bob", "2026-01-05"),
        issue(6, "alice", "2026-01-06"),
    ]
    return {
        f"{REPO}/contributors": [
            {"login": "alice", "contributions": 10},
            {"login": "bob", "contributions": 5},
            {"login": "carol", "contributions": 1},
        ],
        f"{REPO}/pulls": pulls,
        f"{REPO}/issues": issues,
        f"{REPO}/issues/comments": [
            issue_comment(5, "alice", "2026-02-01"),
            issue_comment(5, "alice", "2026-02-02"),  # a second comment: counts once
            issue_comment(5, "carol", "2026-02-03"),
            issue_comment(6, "bob", "2026-02-04"),
            issue_comment(2, "alice", "2026-02-05"),  # on a pull request
            issue_comment(2, "bob", "2026-02-06"),  # on their own pull request
            issue_comment(4, "alice", "2026-02-07"),
        ],
        f"{REPO}/pulls/comments": [
            review_comment(1, "bob", "2026-02-08"),
            review_comment(3, "alice", "2026-02-09"),  # on their own pull request
        ],
        f"{REPO}/pulls/1/reviews": [review("bob", "APPROVED", "2026-02-10")],
        f"{REPO}/pulls/2/reviews": [
            review("alice", "COMMENTED", "2026-02-11"),
            review("bob", "COMMENTED", "2026-02-12"),  # their own pull request
        ],
        f"{REPO}/pulls/3/reviews": [
            review("carol", "APPROVED", "2026-02-13"),
            review("alice", "PENDING", "2026-03-30"),
        ],
        f"{REPO}/pulls/4/reviews": [review("bob", "APPROVED", "2026-02-14")],
        f"{REPO}/issues/events": [  # newest first, like GitHub
            {
                "actor": user("bob"),
                "event": "merged",
                "created_at": "2026-06-05T10:00:00Z",
            },
            {"actor": None, "event": "closed", "created_at": "2026-06-04T10:00:00Z"},
            {
                "actor": user("carol"),
                "event": "labeled",
                "created_at": "2026-06-01T10:00:00Z",
            },
        ],
        f"{REPO}/comments": [  # on commits
            {"user": user("alice"), "created_at": "2026-07-01T10:00:00Z"}
        ],
        # newest commit per author
        f"{REPO}/commits": {
            "alice": "2026-03-01",
            "bob": "2026-02-01",
            "carol": "2025-12-01",
        },
    }


class FakeGitHub(ThreadingHTTPServer):
    """Serves one repository with ETags, pagination and a rate limit."""

    def __init__(self):
        super().__init__(("127.0.0.1", 0), Handler)
        self.data = make_data()
        self.log = []  # (path with page, conditional?, status)
        self.used = 0
        self.after = None  # called with the name of each downloaded page
        self.active = 0
        self.max_active = 0
        self.lock = threading.Lock()

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server_port}"

    def requests(self, conditional=None, status=None):
        return [
            path
            for path, cond, stat in self.log
            if (conditional is None or cond == conditional)
            and (status is None or stat == status)
            and "/rate_limit" not in path
        ]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        server = self.server
        with server.lock:
            server.active += 1
            server.max_active = max(server.max_active, server.active)
        try:
            time.sleep(0.02)  # so that parallel requests overlap
            self.get()
        finally:
            with server.lock:
                server.active -= 1

    def get(self):
        url = urlparse(self.path)
        query = parse_qs(url.query)
        server = self.server
        if url.path == "/rate_limit":
            used = server.used
            body = {"resources": {"core": {"limit": 5000, "remaining": 5000 - used}}}
            return self.reply(200, body, etag=False, count=False)
        if url.path == REPO:
            return self.reply(200, {"full_name": "a/b"})
        if url.path == f"{REPO}/commits":
            date = server.data[url.path].get(query["author"][0])
            body = (
                [{"commit": {"author": {"date": f"{date}T10:00:00Z"}}}] if date else []
            )
            return self.reply(200, body, name=self.path)
        items = server.data.get(url.path, [])  # e.g. no reviews
        per_page = int(query["per_page"][0])
        page = int(query.get("page", ["1"])[0])
        last = max(1, -(-len(items) // per_page))
        base = f"<{server.url}{url.path}?per_page={per_page}"
        links = []
        if page < last:
            links.append(f'{base}&page={page + 1}>; rel="next"')
            links.append(f'{base}&page={last}>; rel="last"')
        chunk = items[(page - 1) * per_page : page * per_page]
        self.reply(200, chunk, links=links, name=f"{url.path}?page={page}")

    def reply(self, status, body, etag=True, links=(), name=None, count=True):
        server = self.server
        data = json.dumps(body).encode()
        tag = '"' + hashlib.md5(data).hexdigest() + '"' if etag else None
        conditional = self.headers.get("If-None-Match") is not None
        if tag and self.headers.get("If-None-Match") == tag:
            status, data = 304, b""
        elif count:
            with server.lock:
                server.used += 1
        with server.lock:
            server.log.append((name or self.path, conditional, status))
        self.send_response(status)
        if tag:
            self.send_header("ETag", tag)
        if links:  # also on 304, like GitHub
            self.send_header("Link", ", ".join(links))
        self.send_header("X-RateLimit-Limit", "5000")
        self.send_header("X-RateLimit-Remaining", str(5000 - server.used))
        self.send_header("X-RateLimit-Reset", "1800000000")
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
        if server.after and status == 200:
            server.after(name or self.path)


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setattr(contributors, "PER_PAGE", PER_PAGE)
    monkeypatch.setattr(contributors, "REQUEST_DELAY", 0)
    server = FakeGitHub()
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server
    server.shutdown()
    server.server_close()


def analyse(api, cache, token="t", jobs=4):
    messages = []
    rows = contributors.collect(
        token, ["a/b"], messages.append, cache=cache, base_url=api.url, jobs=jobs
    )
    return {r["handle"]: r for r in rows}, messages


def counts(row):
    return {
        key: row[key]
        for key in ("commits", "prs", "merged", "opened", "commented")
        + ("pr_commented", "reviewed")
    }


def test_counts(api):
    rows, _ = analyse(api, None)
    assert counts(rows["alice"]) == dict(
        commits=10, prs=2, merged=2, opened=1, commented=1, pr_commented=2, reviewed=1
    )
    assert counts(rows["bob"]) == dict(
        commits=5, prs=1, merged=0, opened=1, commented=1, pr_commented=1, reviewed=2
    )
    assert counts(rows["carol"]) == dict(
        commits=1, prs=1, merged=1, opened=0, commented=1, pr_commented=0, reviewed=1
    )


def test_latest_activity(api):
    rows, _ = analyse(api, None)
    date = {login: row["activity"].date().isoformat() for login, row in rows.items()}
    # alice: a comment on a commit, after her newest commit (2026-03-01);
    # bob merged something; carol labeled something, after her review.
    # The pending review (2026-03-30) does not count.
    assert date == {"alice": "2026-07-01", "bob": "2026-06-05", "carol": "2026-06-01"}


def test_progress_shows_pages_cached_and_api_calls(api, tmp_path):
    _, messages = analyse(api, ResponseCache(tmp_path))
    first = messages[0]
    assert first.startswith("[1/1] a/b: contributors page 1/2")
    assert re.search(r" \| cached     0 \| API    \d/5000$", first)
    assert any("pull requests page 2/2" in m for m in messages)
    assert any("latest commits 3/3" in m for m in messages)
    assert any("reviews of pull request 4/4" in m for m in messages)
    # the status column lines up
    steps = [m for m in messages if not m.startswith(" ")]
    assert len({m.index(" | cached") for m in steps}) == 1
    assert re.search(r"Done: 3 contributors in 1 repositories +\| cached", messages[-1])
    assert re.search(r"\| resets \d\d:\d\d$", messages[-1])


def test_progress_without_cache_has_no_cached_count(api):
    _, messages = analyse(api, None)
    assert "cached" not in messages[0]
    assert re.search(r" \| API +\d+/5000$", messages[0])


def test_requests_are_parallel(api):
    rows, _ = analyse(api, None, jobs=4)
    assert api.max_active > 1
    api.max_active = 0
    serial, _ = analyse(api, None, jobs=1)
    assert api.max_active == 1
    assert serial == rows


def test_second_analysis_uses_no_api_calls(api, tmp_path):
    first, _ = analyse(api, ResponseCache(tmp_path))
    used = api.used
    assert used > 0
    api.log.clear()

    second, messages = analyse(api, ResponseCache(tmp_path))
    assert second == first
    assert api.used == used  # every request was answered with 304
    assert api.requests(status=200) == []
    assert api.requests(conditional=True, status=304)
    cached = int(re.search(r"cached +(\d+)", messages[-1]).group(1))
    assert cached == len(api.requests(status=304))
    assert f"API {used:>4}/5000" in messages[-1]


def test_only_new_data_is_downloaded(api, tmp_path):
    analyse(api, ResponseCache(tmp_path))
    # a new pull request, listed after the others, with a review and a comment
    api.data[f"{REPO}/pulls"].append(pull(7, "bob", "2026-04-01", True))
    api.data[f"{REPO}/pulls/7/reviews"] = [review("carol", "APPROVED", "2026-04-02")]
    api.data[f"{REPO}/issues/comments"].append(issue_comment(7, "alice", "2026-04-03"))
    api.log.clear()

    rows, _ = analyse(api, ResponseCache(tmp_path))
    assert (rows["bob"]["prs"], rows["bob"]["merged"]) == (2, 1)
    assert rows["carol"]["reviewed"] == 2
    assert rows["alice"]["pr_commented"] == 3
    downloaded = api.requests(status=200)
    # The pages of older pull requests and their reviews are not downloaded again.
    assert not any("/pulls?page=1" in p for p in downloaded)
    assert not any(re.search(r"/pulls/[1-4]/reviews", p) for p in downloaded)
    assert any("/pulls?page=3" in p for p in downloaded)
    assert any("/pulls/7/reviews" in p for p in downloaded)


def test_cache_is_not_shared_between_tokens(api, tmp_path):
    analyse(api, ResponseCache(tmp_path), token="one")
    api.log.clear()
    analyse(api, ResponseCache(tmp_path), token="two")
    # Nothing is known for this token: each page is first requested without
    # validation. (Later requests of a page are conditional: they check that
    # the list did not change while it was read.)
    seen = set()
    for path, conditional, _ in api.log:
        if path not in seen:
            assert not conditional, path
            seen.add(path)


def test_no_cache_always_downloads(api):
    analyse(api, None)
    api.log.clear()
    analyse(api, None)
    assert api.requests(conditional=True) == []
    assert api.requests(status=304) == []


def test_cache_directory_is_private(tmp_path):
    cache = ResponseCache(tmp_path / "c")
    assert (tmp_path / "c").stat().st_mode & 0o777 == 0o700
    cache.store("k", {"etag": "x"})
    assert (tmp_path / "c" / "k.json").stat().st_mode & 0o777 == 0o600


def test_corrupt_cache_entry_is_ignored(tmp_path):
    cache = ResponseCache(tmp_path)
    (tmp_path / "k.json").write_text("{not json")
    assert cache.load("k") is None


def contributor(login, contributions):
    return {"login": login, "contributions": contributions}


def after_first(api, page, action):
    """Run action after the first download of the page: new activity."""
    done = []

    def hook(name):
        if name.endswith(page) and not done:
            done.append(name)
            action()

    api.after = hook


def test_new_contributor_while_reading_updates_not_adds(api):
    contributors_ = api.data[f"{REPO}/contributors"]
    # Page 2 then starts with bob again: he is on two pages.
    after_first(
        api,
        "/contributors?page=1",
        lambda: contributors_.insert(0, contributor("dave", 50)),
    )
    rows, messages = analyse(api, None)
    assert {h: r["commits"] for h, r in rows.items()} == {
        "dave": 50,
        "alice": 10,
        "bob": 5,
        "carol": 1,
    }
    assert any("contributors changed while reading" in m for m in messages)


def test_new_pull_request_while_reading_is_included(api):
    pulls = api.data[f"{REPO}/pulls"]
    after_first(
        api,
        "/pulls?page=2",
        lambda: pulls.append(pull(7, "bob", "2026-04-01", True)),
    )
    rows, messages = analyse(api, None)
    assert (rows["bob"]["prs"], rows["bob"]["merged"]) == (2, 1)
    assert any("pull requests changed while reading" in m for m in messages)


def test_list_that_never_settles_is_still_counted_once(api):
    contributors_ = api.data[f"{REPO}/contributors"]
    counter = iter(range(100))
    api.after = lambda name: (
        contributors_.insert(0, contributor(f"new{next(counter)}", 1))
        if name.endswith("/contributors?page=1")
        else None
    )
    rows, messages = analyse(api, None)
    assert (rows["alice"]["commits"], rows["bob"]["commits"]) == (10, 5)
    assert rows["carol"]["commits"] == 1
    assert sum("contributors changed while reading" in m for m in messages) == 3


def test_item_on_two_pages_is_counted_once(api):
    api.data[f"{REPO}/pulls"].insert(1, pull(1, "alice", "2026-01-01", True))
    rows, _ = analyse(api, None)
    assert (rows["alice"]["prs"], rows["alice"]["merged"]) == (2, 2)


def test_repeated_analysis_updates_the_numbers(api, tmp_path):
    first, _ = analyse(api, ResponseCache(tmp_path))
    api.data[f"{REPO}/contributors"][1]["contributions"] = 6
    api.data[f"{REPO}/pulls"][1] = pull(2, "bob", "2026-01-02", True)  # now merged
    second, _ = analyse(api, ResponseCache(tmp_path))
    assert (first["bob"]["commits"], first["bob"]["merged"]) == (5, 0)
    assert (second["bob"]["commits"], second["bob"]["merged"]) == (6, 1)
    assert second["bob"]["prs"] == 1


def summaries(messages):
    return {
        m.split(":")[0].strip(): m.split(": ", 1)[1] for m in messages if m[0] == " "
    }


def test_summary_of_each_step_tells_how_the_api_calls_were_used(api, tmp_path):
    _, messages = analyse(api, ResponseCache(tmp_path), jobs=4)
    steps = summaries(messages)
    assert list(steps) == [
        "contributors",
        "latest commits",
        "pull requests",
        "issues",
        "comments",
        "review comments",
        "issue events",
        "commit comments",
        "reviews",
    ]
    # one request per contributor, sent in parallel
    assert re.fullmatch(
        r"3 requests \([2-4] at once\), 0 cached, 3 fetched, "
        r"0 unchanged, not requested, API \+3",
        steps["latest commits"],
    )
    # one request per pull request
    assert re.fullmatch(
        r"4 requests \([2-4] at once\), 0 cached, 4 fetched, "
        r"0 unchanged, not requested, API \+4",
        steps["reviews"],
    )

    api.data[f"{REPO}/pulls"].append(pull(7, "bob", "2026-04-01", True))
    _, messages = analyse(api, ResponseCache(tmp_path), jobs=4)
    steps = summaries(messages)
    # nothing changed for the contributors: not even a request to validate
    assert (
        steps["latest commits"] == "0 requests (one at a time), 0 cached, 0 fetched, "
        "3 unchanged, not requested, API +0"
    )
    # only the new pull request is requested
    assert (
        steps["reviews"] == "1 request (one at a time), 0 cached, 1 fetched, "
        "4 unchanged, not requested, API +1"
    )


def test_changes_are_found_where_nothing_is_requested_otherwise(api, tmp_path):
    analyse(api, ResponseCache(tmp_path))
    api.log.clear()
    # A review on an old pull request updates the pull request.
    api.data[f"{REPO}/pulls"][1]["updated_at"] = "2026-05-01T10:00:00Z"
    api.data[f"{REPO}/pulls/2/reviews"].append(
        review("carol", "APPROVED", "2026-05-01")
    )
    # New commits of alice change the number of her commits.
    api.data[f"{REPO}/contributors"][0]["contributions"] = 11
    api.data[f"{REPO}/commits"]["alice"] = "2026-08-02"
    rows, _ = analyse(api, ResponseCache(tmp_path))
    assert rows["carol"]["reviewed"] == 2
    assert rows["alice"]["commits"] == 11
    assert rows["alice"]["activity"].date().isoformat() == "2026-08-02"
    requested = api.requests()
    assert any("/pulls/2/reviews" in p for p in requested)
    assert not any(re.search(r"/pulls/[134]/reviews", p) for p in requested)
    assert [p for p in requested if "/commits?author" in p] == [
        "/repos/a/b/commits?author=alice&per_page=1"
    ]


def test_summary_says_when_requests_are_one_at_a_time(api):
    _, messages = analyse(api, None, jobs=1)
    assert summaries(messages)["reviews"] == "4 requests (one at a time), API +4"
