from datetime import timedelta

from ..models import Item
from ..stats.responses import bot_test, first_response, responses_to, waits


def items_with_responses(items, classifier=None) -> list[Item]:
    """The pull requests and issues with their first response and whether they wait.

    The responses are those of ``stats.responses.responses_to``, the one definition of a
    response of the site: the first one that is not of a bot is the first response, and an open
    item waits while no collaborator or higher responded.

    Args:
        items: The pull requests and issues, as a query.
        classifier: Decides which accounts are bots (see ``stats.responses.bot_test``); None
            for those GitHub marks.

    Returns:
        The items, each with ``first_response_at``, ``response`` (the time until then, None
        without one) and ``waiting``.
    """
    is_bot = bot_test(classifier)
    found = responses_to(items)
    rows = list(items.select_related("repository"))
    for item in rows:
        first = first_response(found[item.pk], is_bot)
        item.first_response_at = first.at if first else None  # pyright: ignore[reportAttributeAccessIssue]
        item.response = timedelta(seconds=first.seconds) if first else None  # pyright: ignore[reportAttributeAccessIssue]
        item.waiting = waits(item.state, found[item.pk], is_bot)  # pyright: ignore[reportAttributeAccessIssue]
    return rows
