from urllib.parse import urlencode

from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache

from .. import export, query, spreadsheet, stats
from ..classify import class_list
from ..feedback import show_error
from ..models import (
    Person,
    SavedQuery,
)
from .exports import ODS, about_export, download
from .scope import scope_of, scope_view, stats_page

QUERY_FIELDS = ("where", "sort", "columns", "group", "chart")


CHART_TOP = 25


def query_parameters(request) -> dict[str, str]:
    """The query of the contributors page from the address or the form."""
    data = request.POST if request.method == "POST" else request.GET
    return {name: data.get(name, "").strip() for name in QUERY_FIELDS}


def run_query(scope, parameters: dict) -> query.Result:
    """The contributors of the scope, filtered, sorted and grouped by the query."""
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
    """
    scope = scope_of(request, scope)
    parameters = query_parameters(request)
    if request.method == "POST" and request.user.is_authenticated:  # saved queries
        action = request.POST.get("action")
        if action == "save" and request.POST.get("name", "").strip():
            SavedQuery.objects.update_or_create(
                user=request.user,
                name=request.POST["name"].strip()[:100],
                defaults=parameters,
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
    chart = parameters["chart"] if parameters["chart"] in query.NUMBERS else "activity"
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
    """
    scope = scope_of(request, scope)
    parameters = query_parameters(request)
    try:
        result = run_query(scope, parameters)
    except Exception as error:
        show_error(request, error)
        return redirect(f"/s/{scope.text}/contributors/?{urlencode(parameters)}")
    rows = [
        {
            name: "" if cell == float("inf") else cell
            for name, cell in zip(result.columns, row, strict=True)
        }
        for row in result.rows
    ]
    filename = f"contributors-{scope.text}.{extension}"
    if extension == "csv":
        return download(export.to_csv(rows), "text/csv; charset=utf-8", filename)
    names = [c.name for c in class_list(request.user)]
    query = {f"query {name}": value for name, value in parameters.items()}
    about = about_export(scope, "query of the contributors", names, **query)
    sheets = export.workbook(
        "contributors",
        scope.repositories,
        scope.classifier(),
        names,
        scope.since,
        scope.until,
        about,
        first=[("query result", rows)],
    )
    return download(spreadsheet.to_ods(sheets), ODS, filename)
