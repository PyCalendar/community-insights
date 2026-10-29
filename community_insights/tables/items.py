from django.db.models import DurationField, ExpressionWrapper, F, OuterRef, Subquery
from django.db.models.functions import Lower

from ..models import Event
from ..stats import items_in


def bot_logins(repositories, classifier) -> set[str]:
    """The accounts of the repositories that the classes of people count as bots.

    Args:
        repositories: The repositories.
        classifier: Decides the class of each actor; its first class with the rule "is a bot"
            is the class of the bots.

    Returns:
        The logins in lower case; none if no class has the rule "is a bot".
    """
    bots = classifier.bot_class()
    if bots is None:
        return set()
    actors = (
        Event.objects.filter(item__repository__in=repositories)
        .values_list("actor", "association", "is_bot")
        .distinct()
    )
    return {
        actor.lower()
        for actor, association, is_bot in actors
        if classifier(actor, association, is_bot) == bots
    }


def items_with_responses(repositories, since=None, until=None, classifier=None):
    """The pull requests and issues with the time of their first response.

    The pull requests and issues of the time range with the time of their first response: a
    comment or review by somebody else than the author, and not by a bot, so that a bot that
    comments at once does not hide the review of a person.

    Args:
        repositories: The repositories.
        since: The start of the time range, None for the beginning.
        until: The end of the time range, excluded; None for now.
        classifier: Decides which accounts are bots (see ``bot_logins``); None counts everyone.

    Returns:
        The items as a query, each with the time of its first response.
    """
    bots = bot_logins(repositories, classifier) if classifier is not None else set()
    first = (
        Event.objects.filter(item=OuterRef("pk"))
        .exclude(kind=Event.OPENED)
        .annotate(who=Lower("actor"))
        .exclude(who=OuterRef("author_lower"))
        .exclude(who__in=bots)
        .order_by("at")
        .values("at")[:1]
    )
    return (
        items_in(repositories, since, until)
        .select_related("repository")
        .annotate(author_lower=Lower("author"))
        .annotate(first_response_at=Subquery(first))
        .annotate(
            response=ExpressionWrapper(
                F("first_response_at") - F("created_at"), output_field=DurationField()
            )
        )
    )
