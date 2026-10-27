from community_insights.github import RateLimit


def user(login, kind="User"):
    """A user as the REST API answers it."""
    return {"login": login, "type": kind}


def rest_issue(number, author, created, updated=None, pull=False, merged=False, state="open"):
    """An issue or pull request as the REST API answers it."""
    issue = {
        "node_id": f"n{number}",
        "number": number,
        "title": f"Item {number}",
        "state": state,
        "created_at": created,
        "updated_at": updated or created,
        "closed_at": None if state == "open" else updated or created,
        "user": user(author),
        "author_association": "CONTRIBUTOR",
    }
    if pull:
        issue["pull_request"] = {"merged_at": created if merged else None}
    return issue


def rest_comment(number, login, at, review=False, kind="User", association="MEMBER"):
    """A comment or review comment as the REST API answers it."""
    url = f"https://api.github.com/repos/o/r/{'pulls' if review else 'issues'}/{number}"
    return {
        ("pull_request_url" if review else "issue_url"): url,
        "user": user(login, kind),
        "created_at": at,
        "author_association": association,
    }


class FakeREST:
    """The REST endpoints of a repository without a token: issues and pull
    requests, issue comments and review comments; `since` is obeyed."""

    def __init__(self, issues=(), comments=(), reviews=(), commits=()):
        """The data to answer with."""
        self.issues, self.comments, self.reviews = list(issues), list(comments), list(reviews)
        self.commits = list(commits)  # REST commits
        self.requests = 0
        self.rate = RateLimit()
        self.asked: list[tuple[str, dict]] = []

    async def all_pages(self, path, **params):
        """All entries of a list, changed since the parameter since."""
        self.requests += 1
        self.asked.append((path, params))
        since = params.get("since", "")
        if path.endswith("/commits"):
            return [c for c in self.commits if c["commit"]["committer"]["date"] > since]
        if path.endswith("/issues"):
            found = [i for i in self.issues if i["updated_at"] > since]
        elif path.endswith("/issues/comments"):
            found = [c for c in self.comments if c["created_at"] > since]
        else:
            found = [c for c in self.reviews if c["created_at"] > since]
        return found

    async def close(self):
        """Nothing to close."""
        pass
