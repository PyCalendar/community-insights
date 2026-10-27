"""Accounts that answer like bots: most of their first responses come within minutes."""

from dataclasses import dataclass

from ..models import Event, Item

FAST = 120  # seconds: a person rarely answers that fast
AT_LEAST = 10  # pull requests and issues: fewer say little


@dataclass
class BotSuggestion:
    """An account that may be a bot: on how many items it responded, and how often fast.

    Attributes:
        login: The handle.
        items: On how many items of others it responded first.
        fast: How many of these responses came fast.
    """

    login: str
    items: int
    fast: int


def bot_suggestions(repositories, fast: float = FAST, at_least: int = AT_LEAST):
    """The accounts whose first responses mostly come within `fast` seconds.

    GitHub marks apps as bots, but some bots are accounts like those of people, such as
    coveralls. An account is suggested when it responded to at least `at_least` pull requests
    and issues of others and more than half of these first responses came within `fast`
    seconds. Accounts GitHub marks as bots are not suggested: they are bots already.

    Args:
        repositories: The repositories to look at.
        fast: The seconds a response may take to count as fast.
        at_least: The fewest items an account must have responded to.

    Returns:
        The suggestions, the account with the most responses first.
    """
    items = {
        pk: (author.lower(), created)
        for pk, author, created in Item.objects.filter(repository__in=repositories).values_list(
            "id", "author", "created_at"
        )
    }
    first: dict[tuple[int, str], float] = {}
    names: dict[str, str] = {}
    events = (
        Event.objects.filter(item__in=items.keys(), is_bot=False)
        .exclude(kind=Event.OPENED)
        .order_by("at")
        .values_list("item_id", "actor", "at")
    )
    for pk, actor, at in events.iterator():
        author, created = items[pk]
        login = actor.lower()
        if login == author:
            continue
        names.setdefault(login, actor)
        first.setdefault((pk, login), (at - created).total_seconds())
    counted: dict[str, list[int]] = {}
    for (_, login), seconds in first.items():
        total = counted.setdefault(login, [0, 0])
        total[0] += 1
        total[1] += seconds <= fast
    found = [
        BotSuggestion(names[login], number, quick)
        for login, (number, quick) in counted.items()
        if number >= at_least and quick * 2 > number
    ]
    return sorted(found, key=lambda s: (-s.items, s.login.lower()))
