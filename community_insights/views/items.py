from django_tables2 import RequestConfig

from ..tables import ItemFilter, ItemTable, items_with_responses
from .scope import scope_of, scope_view, stats_page


@scope_view
def items(request, scope):
    """The pull requests and issues with their first response.

    The pull requests and issues with their first response: filtered with django-filter, sorted
    and in pages with django-tables2.

    Args:
        request: The request, with the filters, the sorting and the page.
        scope: The text of the scope.

    Returns:
        The page.
    """
    scope = scope_of(request, scope)
    found = ItemFilter(
        request.GET, queryset=items_with_responses(scope.repositories, scope.since, scope.until)
    )
    table = ItemTable(found.qs)
    # django-tables2 takes the options of the paginator; its type hints say only bool
    RequestConfig(request, paginate={"per_page": 50}).configure(table)  # pyright: ignore[reportArgumentType]
    return stats_page(
        request,
        scope,
        "community/items.html",
        {"table": table, "filter": found, "parameters": dict(request.GET.items())},
    )
