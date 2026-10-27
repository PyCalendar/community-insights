from django.db.models import DurationField, ExpressionWrapper, F, OuterRef, Subquery
from django.db.models.functions import Lower

from ..models import Event
from ..stats import items_in


def items_with_responses(repositories, since=None, until=None):
    """The pull requests and issues with the time of their first response.

    The pull requests and issues of the time range with the time of their first response: a
    comment or review by somebody else than the author.

    Args:
        repositories: The repositories.
        since: The start of the time range, None for the beginning.
        until: The end of the time range, excluded; None for now.

    Returns:
        The items as a query, each with the time of its first response.
    """
    first = (
        Event.objects.filter(item=OuterRef("pk"))
        .exclude(kind=Event.OPENED)
        .annotate(who=Lower("actor"))
        .exclude(who=OuterRef("author_lower"))
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
