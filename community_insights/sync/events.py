"""Events of the database from the answers of GitHub.

Pull requests, issues, comments and reviews as GitHub answers them become the events of the
database.
"""

from django.utils.dateparse import parse_datetime

from ..models import Event


def is_bot(login: str, typename: str | None = None) -> bool:
    """Whether an account is a bot: of type Bot, [bot] in its name, or Copilot."""
    return typename == "Bot" or login.lower().endswith("[bot]") or login.lower() == "copilot"


def opened(item: dict) -> list[Event]:
    """The opening of the item by its author; none for a deleted user."""
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
    """Comments ("comments") or reviews ("reviews"), without deleted users."""
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
                )
            )
    return found
