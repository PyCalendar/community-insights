"""GitHub data as GitHub answers it, to build test data."""


def node(login, at, association="NONE", typename="User", key="createdAt", state=None):
    """A comment or review as GitHub answers it; a review can have its state, such as APPROVED."""
    found = {
        key: at,
        "author": {"login": login, "__typename": typename},
        "authorAssociation": association,
    }
    if state:
        found["state"] = state
    return found


def connection(*nodes):
    """One page of nodes, without more pages."""
    return {"pageInfo": {"hasNextPage": False, "endCursor": None}, "nodes": list(nodes)}


def item(
    number,
    author,
    created,
    comments=(),
    reviews=None,
    state="OPEN",
    merged=False,
    updated=None,
    commits=None,
    closer=None,
):
    """A pull request or issue as GitHub answers it.

    ``commits`` are (login, time) pairs of the last commits of a pull request, ``closer`` who
    closed it; without them, the answer has none, as before commits were read.
    """
    data = {
        "id": f"id{number}",
        "number": number,
        "title": f"Item {number}",
        "state": state,
        "createdAt": created,
        "updatedAt": updated or created,
        "closedAt": None,
        "author": {"login": author, "__typename": "User"},
        "authorAssociation": "CONTRIBUTOR",
        "comments": connection(*comments),
    }
    if reviews is not None:
        data.update(merged=merged, mergedAt=None, mergedBy=None, reviews=connection(*reviews))
    if commits is not None:
        data["commits"] = {
            "nodes": [
                {"commit": {"committedDate": at, "author": {"user": {"login": login}}}}
                for login, at in commits
            ]
        }
    if closer is not None:
        data["closedAt"] = updated or created
        data["timelineItems"] = {"nodes": [{"actor": {"login": closer}}]}
    return data


def commit(sha, login, at, name=None):
    """A commit as GitHub answers it."""
    user = {"login": login} if login else None
    return {"oid": sha, "committedDate": at, "author": {"name": name or login, "user": user}}


def repo(name, stars=0, private=False):
    """A repository as GitHub answers it."""
    return {
        "nameWithOwner": name,
        "description": "",
        "stargazerCount": stars,
        "isPrivate": private,
        "isArchived": False,
    }
