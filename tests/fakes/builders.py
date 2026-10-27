"""GitHub data as GitHub answers it, to build test data."""


def node(login, at, association="NONE", typename="User", key="createdAt"):
    return {
        key: at,
        "author": {"login": login, "__typename": typename},
        "authorAssociation": association,
    }


def connection(*nodes):
    return {"pageInfo": {"hasNextPage": False, "endCursor": None}, "nodes": list(nodes)}


def item(
    number, author, created, comments=(), reviews=None, state="OPEN", merged=False, updated=None
):
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
    return data


def commit(sha, login, at, name=None):
    user = {"login": login} if login else None
    return {"oid": sha, "committedDate": at, "author": {"name": name or login, "user": user}}


def repo(name, stars=0, private=False):
    return {
        "nameWithOwner": name,
        "description": "",
        "stargazerCount": stars,
        "isPrivate": private,
        "isArchived": False,
    }
