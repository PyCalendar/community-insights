from urllib.parse import urlencode

from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views.decorators.cache import never_cache

from .. import export, query, stats
from ..errors import InvalidQuery
from ..feedback import show_error
from ..models import (
    Person,
    SavedQuery,
)
from .exports import download
from .scope import scope_of, scope_view, stats_page

QUERY_FIELDS = ("where", "sort", "columns", "group", "chart")


CHART_TOP = 25


# example queries for the field Who: a title, the query, how to sort and the last days
EXAMPLES = [
    (gettext_lazy("Most commits in the last month"), "commits_total > 0", "-commits_total", 30),
    (
        gettext_lazy("External contributors who opened a pull request in the last month"),
        'user_class == "external" and prs_total > 0',
        "-prs_total",
        30,
    ),
    (
        gettext_lazy("New, but contributed continuously in the last two months"),
        "days_last < 60 and not user_bot and prs_total > 3 and commits_total < 300"
        " and prs_reviewed < 1",
        "-prs_total",
        60,
    ),
    (
        gettext_lazy("Who opened a pull request, the most merged first"),
        "prs_total > 0",
        "-prs_merged",
        None,
    ),
    (
        gettext_lazy("Who reviews the pull requests of others"),
        "prs_reviewed > 0 and not user_bot",
        "-prs_reviewed",
        None,
    ),
    (
        gettext_lazy("Who answers within a day"),
        "hours_to_respond <= 24 and not user_bot",
        "hours_to_respond",
        None,
    ),
    (
        gettext_lazy("People in a country of Horizon Europe"),
        "user_horizon_europe and not user_bot",
        "-activity_total",
        None,
    ),
    (
        gettext_lazy("Opened issues, but no pull request"),
        "issues_opened > 0 and prs_total == 0",
        "-issues_opened",
        None,
    ),
]


def sort_links(scope, parameters: dict, columns: list[str]) -> dict[str, tuple[str, str]]:
    """The links of the column headers that sort the table by them.

    A column sorts the biggest first for numbers and from A for text; the column the table is
    sorted by now sorts the other way.

    Args:
        scope: The scope shown, for its time range.
        parameters: The query now.
        columns: The columns of the table.

    Returns:
        For each column: the address, and ``"up"``, ``"down"`` or ``""`` for how it is sorted now.
    """
    try:
        by, descending = query.parse_sort(parameters["sort"])
    except InvalidQuery:  # the page shows the error; the headers sort as if there were none
        by, descending = "", False
    found = {}
    for column in columns:
        if column == by:
            wanted, now = ("" if descending else "-") + column, "down" if descending else "up"
        else:
            wanted, now = ("-" if column in query.NUMBERS else "") + column, ""
        address = "?" + urlencode(parameters | {"sort": wanted}) + scope.query_more
        found[column] = (address, now)
    return found


def example_queries(scope) -> list[tuple[str, str]]:
    """The example queries as links, with their time range or the one of the page.

    Args:
        scope: The scope shown.

    Returns:
        Pairs of the title and the address of the page with the query.
    """
    found = []
    for title, where, sort, last in EXAMPLES:
        parameters = {"where": where, "sort": sort}
        # the time range is a part of the example; the others keep the one of the page
        address = "?" + urlencode(parameters | {"last": last} | scope.carried) if last else None
        found.append((str(title), address or "?" + urlencode(parameters) + scope.query_more))
    return found


def query_parameters(request) -> dict[str, str]:
    """The query of the contributors page from the address or the form.

    Args:
        request: The request.

    Returns:
        The value of each field of the query: where, sort, columns, group and chart.
    """
    data = request.POST if request.method == "POST" else request.GET
    return {name: data.get(name, "").strip() for name in QUERY_FIELDS}


def run_query(scope, parameters: dict) -> query.Result:
    """The contributors of the scope, filtered, sorted and grouped by the query.

    Args:
        scope: The scope.
        parameters: The fields of the query.

    Returns:
        The result of the query.
    """
    people = stats.contributors(
        scope.repositories, scope.classifier(), since=scope.since, until=scope.until
    )
    return query.run(
        people,
        timezone.now(),
        where=parameters["where"],
        sort=parameters["sort"],
        columns=parameters["columns"],
        group=parameters["group"],
    )


@scope_view
def contributors(request, scope):
    """The contributors as a table and a chart, by a query.

    The contributors as a table, filtered, sorted and grouped by a query, with a chart of the
    result; queries can be saved.

    Args:
        request: The request, with the query in its address; a POST saves or deletes a query.
        scope: The text of the scope.

    Returns:
        The page, or a redirect to it after a change.
    """
    scope = scope_of(request, scope)
    parameters = query_parameters(request)
    if request.method == "POST" and request.user.is_authenticated:  # saved queries
        action = request.POST.get("action")
        if action == "save" and request.POST.get("name", "").strip():
            time_range = {
                name: request.POST.get(name, "").strip()[:10] for name in ("since", "until", "last")
            }
            SavedQuery.objects.update_or_create(
                user=request.user,
                name=request.POST["name"].strip()[:100],
                defaults=parameters | time_range,
            )
            messages.success(request, _("The query was saved."))
        elif action == "delete":
            SavedQuery.objects.filter(user=request.user, pk=request.POST.get("id")).delete()
        return redirect(f"{request.path}?{urlencode(parameters)}")
    try:
        result = run_query(scope, parameters)
    except Exception as error:  # shown with what to do
        show_error(request, error)
        result = None
    else:
        Person.objects.filter(login__in=[c.login for c in result.contributors]).update(
            last_used_at=timezone.now()
        )
    chart = parameters["chart"] if parameters["chart"] in query.NUMBERS else "activity_total"
    return stats_page(
        request,
        scope,
        "community/contributors.html",
        {
            "result": result,
            "parameters": parameters,
            "chart": chart,
            "encoded": urlencode({**parameters, "chart": chart}),
            "variables": query.VARIABLES,
            "default_columns": query.DEFAULT_COLUMNS,
            "sorting": sort_links(scope, parameters, result.columns if result else []),
            "examples": example_queries(scope),
            "numbers": query.NUMBERS,
            "groups": query.GROUPS,
            "saved": request.user.queries.all() if request.user.is_authenticated else [],
            "can_save": request.user.is_authenticated,
            "timezone": timezone.get_current_timezone_name(),
        },
    )


@scope_view
@never_cache
def contributors_download(request, scope, extension):
    """The result of a query as CSV or ODS.

    The result of a query as CSV, its columns as chosen; as ODS with all contributors and the
    data they were counted from as more sheets.

    Args:
        request: The request, with the query in its address.
        scope: The text of the scope.
        extension: ``csv`` or ``ods``.

    Returns:
        The file to download.
    """
    scope = scope_of(request, scope)
    parameters = query_parameters(request)
    filename = f"contributors-{scope.text}.{extension}"
    back = f"/s/{scope.text}/contributors/?{urlencode(parameters)}"
    if extension == "ods":
        # more sheets, and it can take long: made in the background, with its progress; the
        # query is only checked here, so that a mistake is shown at once
        from .. import documents
        from ..models import Document

        try:
            query.check(parameters)
        except Exception as error:
            show_error(request, error)
            return redirect(back)
        made = documents.start(
            request,
            Document.QUERY,
            "contributors",
            scope.text,
            parameters | scope.range | scope.carried,
            filename,
        )
        return redirect("document", pk=made.pk)
    try:
        result = run_query(scope, parameters)
    except Exception as error:
        show_error(request, error)
        return redirect(back)
    rows = [
        {
            name: "" if cell == float("inf") else cell
            for name, cell in zip(result.columns, row, strict=True)
        }
        for row in result.rows
    ]
    return download(export.to_csv(rows), "text/csv; charset=utf-8", filename)
