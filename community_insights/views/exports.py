from django.http import Http404, HttpResponse
from django.utils import timezone
from django.views.decorators.cache import never_cache

from .. import export, spreadsheet, version
from ..classify import class_list
from .scope import scope_of, scope_view

ODS = "application/vnd.oasis.opendocument.spreadsheet"


def about_export(scope, table: str, names: list[str], **more) -> dict:
    """What an export is, for its JSON and its "about" sheet."""
    return {
        "table": table,
        "repositories": [r.full_name for r in scope.repositories],
        "since": scope.range.get("since", ""),
        "until": scope.range.get("until", ""),
        "classes": [f"{name}: {export.column(name)}" for name in names],
        "exported_at": export.iso(timezone.now()),
        "version": version.get()["version"],
        **more,
    }


def download(content, content_type: str, filename: str) -> HttpResponse:
    """A response that the browser saves as a file."""
    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@scope_view
@never_cache
def export_table(request, scope, name):
    """A table behind the statistics as CSV, JSON or ODS.

    A table behind the statistics: /data/responses.csv, .json or .ods; the ODS has the tables it
    was made from as more sheets.
    """
    table, _, extension = name.rpartition(".")
    if table not in export.TABLES or extension not in ("csv", "json", "ods"):
        raise Http404("No such table")
    scope = scope_of(request, scope)
    names = [c.name for c in class_list(request.user)]
    filename = f"{table}-{scope.text}.{extension}"
    arguments = (scope.repositories, scope.classifier(), names, scope.since, scope.until)
    if extension == "ods":
        about = about_export(scope, table, names)
        sheets = export.workbook(table, *arguments, about)
        return download(spreadsheet.to_ods(sheets), ODS, filename)
    rows = export.table(table, *arguments)
    if extension == "csv":
        return download(export.to_csv(rows), "text/csv; charset=utf-8", filename)
    about = about_export(scope, table, names)
    about["classes"] = {name: export.column(name) for name in names}
    return download(export.to_json(rows, about), "application/json; charset=utf-8", filename)
