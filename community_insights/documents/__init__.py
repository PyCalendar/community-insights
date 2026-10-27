"""Documents made in the background, such as an ODS of the statistics, and their messages.

Making a large ODS can take longer than a request may: the request starts a ``Document`` and
shows its progress; a thread makes the file (in the request for tests, ``FETCH_WORKER=inline``).
When the file is ready, the user gets a ``Message`` with the link to download it.
"""

import logging
import threading
from datetime import timedelta

from django.conf import settings
from django.db import close_old_connections, transaction
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.translation import gettext

from .. import errors
from ..models import Document, Message

log = logging.getLogger(__name__)
KEEP = timedelta(days=7)  # documents are deleted after a week


def start(request, kind: str, table: str, scope: str, parameters: dict, filename: str):
    """Start making a document for the person of a request.

    Args:
        request: The request; the document belongs to its user, or to the session of a
            visitor, and is made in its time zone and language.
        kind: ``Document.TABLE`` or ``Document.QUERY``.
        table: The table, such as ``responses``; ``contributors`` for a query.
        scope: The text of the scope.
        parameters: The query and the time range of the address.
        filename: The name of the file to download.

    Returns:
        The document, queued.
    """
    clean_up()
    user = request.user if request.user.is_authenticated else None
    if user is None and not request.session.session_key:
        request.session.save()
    document = Document.objects.create(
        user=user,
        session_key="" if user else request.session.session_key,
        kind=kind,
        table=table,
        scope=scope,
        parameters=parameters,
        time_zone=timezone.get_current_timezone_name(),
        language=translation.get_language() or settings.LANGUAGE_CODE,
        filename=filename,
    )
    if settings.FETCH_WORKER == "inline":
        run(document.pk)
    else:
        transaction.on_commit(
            lambda: threading.Thread(
                target=run_in_thread, args=(document.pk,), daemon=True, name="document"
            ).start()
        )
    return document


def sheets_of(document: Document, step):
    """The sheets of the ODS of a document, made one after the other.

    Args:
        document: The document.
        step: Called with the number of sheets made and of all, for the progress.

    Returns:
        The sheets as pairs of a name and rows.
    """
    from django.contrib.auth.models import AnonymousUser

    from .. import export
    from ..views.contributors import run_query
    from ..views.exports import about_export
    from ..views.scope import Scope

    user = document.user or AnonymousUser()
    scope = Scope(user, document.scope, document.parameters)
    names = [c.name for c in scope.classes()]
    arguments = (scope.repositories, scope.classifier(), names, scope.since, scope.until)
    tables = [document.table, *export.SOURCES.get(document.table, ())]
    total = len(tables) + (2 if document.kind == Document.QUERY else 1)
    sheets = []
    if document.kind == Document.QUERY:
        query = {
            name: document.parameters.get(name, "")
            for name in ("where", "sort", "columns", "group", "chart")
        }
        result = run_query(scope, query)
        rows = [
            {
                name: "" if cell == float("inf") else cell
                for name, cell in zip(result.columns, row, strict=True)
            }
            for row in result.rows
        ]
        sheets.append(("query result", rows))
        step(len(sheets), total)
        about = about_export(
            scope, "query of the contributors", names, **{f"query {k}": v for k, v in query.items()}
        )
    else:
        about = about_export(scope, document.table, names)
    for table in tables:
        sheets.append((table, export.table(table, *arguments)))
        step(len(sheets), total)
    sheets.append(("about", export.about_rows(about)))
    return sheets


def run(pk: int) -> Document:
    """Make the file of a document, and tell its user with a message.

    Args:
        pk: The id of the document.

    Returns:
        The document, done or failed; it never raises.
    """
    from .. import spreadsheet

    document = Document.objects.get(pk=pk)
    Document.objects.filter(pk=pk).update(status=Document.RUNNING)

    def step(done: int, total: int) -> None:
        # the file is written after the last sheet: 90 % until then
        Document.objects.filter(pk=pk).update(progress=round(90 * done / total))

    try:
        with timezone.override(document.time_zone), translation.override(document.language):
            content = spreadsheet.to_ods(sheets_of(document, step))
            path = document.path()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    except Exception as error:  # the document says what went wrong
        log.exception("The document %s could not be made", pk)
        known = errors.translate(error)
        document.status, document.message, document.error_code = (
            Document.FAILED,
            str(known),
            known.code,
        )
    else:
        document.status, document.progress = Document.DONE, 100
    document.finished = timezone.now()
    document.save()
    if document.user_id is not None:
        tell(document)
    return document


def run_in_thread(pk: int) -> None:
    """Make a document in a thread of its own, with its own connection to the database.

    Args:
        pk: The id of the document.
    """
    close_old_connections()
    try:
        run(pk)
    finally:
        close_old_connections()


def tell(document: Document) -> Message:
    """The message to the user that a document is ready, or could not be made.

    Args:
        document: The finished document of a user.

    Returns:
        The message.
    """
    with translation.override(document.language):
        if document.status == Document.DONE:
            title = gettext("%(file)s is ready to download") % {"file": document.filename}
            text = gettext("The file was made from the data on this site at %(time)s.") % {
                "time": f"{timezone.localtime(document.finished):%Y-%m-%d %H:%M}"
            }
        else:
            title = gettext("%(file)s could not be made") % {"file": document.filename}
            text = document.message
    return Message.objects.create(
        user=document.user,
        title=title,
        text=text,
        link=reverse("document", args=[document.pk]),
    )


def clean_up(now=None) -> int:
    """Delete the documents older than a week, with their files.

    Args:
        now: The time now, for tests.

    Returns:
        How many documents were deleted.
    """
    old = Document.objects.filter(created__lt=(now or timezone.now()) - KEEP)
    count = 0
    for document in old:
        document.path().unlink(missing_ok=True)
        document.delete()
        count += 1
    return count
