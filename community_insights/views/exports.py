from django.http import Http404, HttpResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.views.decorators.cache import never_cache

from .. import export, version
from .scope import scope_of, scope_view

ODS = "application/vnd.oasis.opendocument.spreadsheet"


def about_export(scope, table: str, names: list[str], **more) -> dict:
    """What an export is, for its JSON and its "about" sheet.

    Args:
        scope: The scope exported.
        table: The name of the table.
        names: The names of the classes.
        **more: More facts, such as the query.

    Returns:
        The facts by their names.
    """
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
    """A response that the browser saves as a file.

    Args:
        content: The content of the file.
        content_type: Its media type.
        filename: The name of the file.

    Returns:
        The response.
    """
    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@scope_view
@never_cache
def export_table(request, scope, name):
    """A table behind the statistics as CSV, JSON or ODS.

    A table behind the statistics: /data/responses.csv, .json or .ods; the ODS has the tables it
    was made from as more sheets.

    Args:
        request: The request.
        scope: The text of the scope.
        name: The table and the extension, such as ``responses.csv``.

    Returns:
        The file; for ODS a redirect to the page of the document made in the background.

    Raises:
        Http404: If there is no such table or extension.
    """
    table, _, extension = name.rpartition(".")
    if table not in export.TABLES or extension not in ("csv", "json", "ods"):
        raise Http404("No such table")
    scope = scope_of(request, scope)
    names = [c.name for c in scope.classes()]
    filename = f"{table}-{scope.text}.{extension}"
    arguments = (scope.repositories, scope.classifier(), names, scope.since, scope.until)
    if extension == "ods":  # can take long: made in the background, with its progress
        from .. import documents
        from ..models import Document

        made = documents.start(
            request, Document.TABLE, table, scope.text, scope.range | scope.carried, filename
        )
        return redirect("document", pk=made.pk)
    rows = export.table(table, *arguments)
    if extension == "csv":
        return download(export.to_csv(rows), "text/csv; charset=utf-8", filename)
    about = about_export(scope, table, names)
    about["classes"] = {name: export.column(name) for name in names}
    return download(export.to_json(rows, about), "application/json; charset=utf-8", filename)
