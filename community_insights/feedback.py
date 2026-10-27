"""Errors shown to people: the title, what happened and a link to what to do."""

from django.contrib import messages
from django.http import JsonResponse
from django.utils.html import format_html
from django.utils.translation import gettext as _

from . import errors


def error_json(error: BaseException, status: int = 500) -> JsonResponse:
    """An error for the JavaScript of the page: title, details and the link."""
    error = errors.translate(error)
    return JsonResponse(
        {
            "error": {
                "code": error.code,
                "title": str(error.title),
                "detail": str(error),
                "docs_url": error.docs_url(),
            }
        },
        status=status,
    )


def show_error(request, error: BaseException, prefix: str = "") -> errors.CommunityError:
    """Show any exception as a message, translated into an error of errors.py."""
    error = errors.translate(error)
    messages.error(
        request,
        format_html(
            '{}<strong>{}</strong>: {} <a href="{}" class="alert-link">{}</a>',
            prefix,
            error.title,
            error,
            error.docs_url(),
            _("What to do"),
        ),
    )
    return error
