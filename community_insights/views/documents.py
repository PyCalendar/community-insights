from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from ..models import Document, Message


def own_document(request, pk) -> Document:
    """A document of the person of a request.

    Args:
        request: The request.
        pk: The id of the document.

    Returns:
        The document.

    Raises:
        Http404: If there is none, or it is somebody else's.
    """
    document = get_object_or_404(Document, pk=pk)
    if not document.owned_by(request):
        raise Http404("No such document")
    return document


@never_cache
def document(request, pk):
    """The page of a document: its progress, and the download when it is ready.

    Args:
        request: The request.
        pk: The id of the document.

    Returns:
        The page.
    """
    return render(request, "community/document.html", {"document": own_document(request, pk)})


@never_cache
def document_progress(request, pk):
    """How far a document is, as JSON, for static/js/document-progress.js.

    Args:
        request: The request.
        pk: The id of the document.

    Returns:
        The status, the percent, what went wrong and the address of the download.
    """
    found = own_document(request, pk)
    return JsonResponse(
        {
            "status": found.status,
            "progress": found.progress,
            "message": found.message,
            "download": f"/documents/{found.pk}/download/" if found.status == Document.DONE else "",
        }
    )


def document_download(request, pk):
    """The file of a document that is ready.

    Args:
        request: The request.
        pk: The id of the document.

    Returns:
        The file; the page of the document while it is not ready.

    Raises:
        Http404: If the file is gone, such as after a week.
    """
    found = own_document(request, pk)
    if found.status != Document.DONE:
        return redirect("document", pk=found.pk)
    path = found.path()
    if not path.is_file():
        raise Http404("The file was deleted")
    return FileResponse(path.open("rb"), as_attachment=True, filename=found.filename)


@login_required
def messages_page(request):
    """The messages of the user, the newest first, unread ones marked.

    Args:
        request: The request.

    Returns:
        The page.
    """
    found = list(request.user.messages.all()[:200])
    return render(request, "community/messages.html", {"inbox": found})


@login_required
def message_open(request, pk):
    """Open a message: it is read, and its link is followed.

    Args:
        request: The request.
        pk: The id of the message.

    Returns:
        A redirect to its link, or to the messages.
    """
    found = get_object_or_404(Message, pk=pk, user=request.user)
    found.mark_read()
    if found.link and url_has_allowed_host_and_scheme(found.link, {request.get_host()}):
        return redirect(found.link)
    return redirect("messages")


@login_required
@require_POST
def messages_read(request):
    """Mark all messages of the user as read.

    Args:
        request: The request.

    Returns:
        A redirect to the messages.
    """
    from django.utils import timezone

    request.user.messages.filter(read_at__isnull=True).update(read_at=timezone.now())
    return redirect("messages")
