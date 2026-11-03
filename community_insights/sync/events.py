"""Events of the database from the answers of GitHub.

Pull requests, issues, comments and reviews as GitHub answers them become the events of the
database.
"""

from django.utils.dateparse import parse_datetime

from ..models import Event, ItemCommit


def is_bot(login: str, typename: str | None = None) -> bool:
    """Whether an account is a bot: of type Bot, [bot] in its name, or Copilot.

    Args:
        login: The handle.
        typename: The type GitHub gives, such as ``Bot``.

    Returns:
        True for bots.
    """
    return typename == "Bot" or login.lower().endswith("[bot]") or login.lower() == "copilot"


def opened(item: dict) -> list[Event]:
    """The opening of the item by its author; none for a deleted user.

    Args:
        item: The item as GitHub answered it.

    Returns:
        The event of the opening, not saved yet.
    """
    author = item.get("author") or {}
    if not author.get("login"):
        return []
    return [
        Event(
            actor=author["login"],
            association=(item.get("authorAssociation") or "").lower(),
            is_bot=is_bot(author["login"], author.get("__typename")),
            kind=Event.OPENED,
            at=parse_datetime(item["createdAt"]),
        )
    ]


def responses(nodes: list[dict], field: str) -> list[Event]:
    """Comments ("comments") or reviews ("reviews"), without deleted users.

    Args:
        nodes: The comments or reviews as GitHub answered them.
        field: ``comments`` or ``reviews``.

    Returns:
        The events, not saved yet.
    """
    found = []
    for node in nodes:
        actor = node.get("author") or {}
        date = node.get("createdAt") or node.get("submittedAt")
        if actor.get("login") and date:
            found.append(
                Event(
                    actor=actor["login"],
                    association=(node.get("authorAssociation") or "").lower(),
                    is_bot=is_bot(actor["login"], actor.get("__typename")),
                    kind=Event.COMMENT if field == "comments" else Event.REVIEW,
                    at=parse_datetime(date),
                    state=(node.get("state") or "").lower(),
                )
            )
    return found


def closer(item: dict) -> str:
    """Who closed a pull request, from its last closing; "" if unknown or open.

    Args:
        item: The pull request as GitHub answered it.

    Returns:
        The login.

    Examples:
        >>> closer({"timelineItems": {"nodes": [{"actor": {"login": "kim"}}]}})
        'kim'
        >>> closer({"timelineItems": {"nodes": [{"actor": None}]}}), closer({})
        ('', '')
    """
    nodes = (item.get("timelineItems") or {}).get("nodes") or []
    return ((nodes[-1] or {}).get("actor") or {}).get("login", "") if nodes else ""


def commits(item: dict) -> list[ItemCommit] | None:
    """The last commits of a pull request, with their author; None if none were read.

    Args:
        item: The pull request as GitHub answered it.

    Returns:
        The commits, not saved yet; None for an answer without commits, such as of an
        issue or of a source that does not read them.
    """
    if "commits" not in item:
        return None
    found = []
    for node in (item["commits"] or {}).get("nodes") or []:
        commit = (node or {}).get("commit") or {}
        if commit.get("committedDate"):
            user = (commit.get("author") or {}).get("user") or {}
            found.append(
                ItemCommit(actor=user.get("login", ""), at=parse_datetime(commit["committedDate"]))
            )
    return found
