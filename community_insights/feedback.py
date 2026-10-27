"""Errors shown to people: the title, what happened and a link to what to do."""

from django.contrib import messages
from django.http import JsonResponse
from django.utils.html import format_html
from django.utils.translation import gettext as _

from . import errors


def error_json(error: BaseException, status: int = 500) -> JsonResponse:
    """An error for the JavaScript of the page: title, details and the link.

    Args:
        error: Any exception; it is translated into an error of errors/.
        status: The HTTP status of the answer.

    Returns:
        The code, the title, the details, the link to what to do and the guide.
    """
    error = errors.translate(error)
    return JsonResponse(
        {
            "error": {
                "code": error.code,
                "title": str(error.title),
                "detail": str(error),
                "docs_url": error.docs_url(),
                "guide_url": error.guide_url(),
                "guide_title": str(error.guide_title),
            }
        },
        status=status,
    )


def show_error(request, error: BaseException, prefix: str = "") -> errors.CommunityError:
    """Show any exception as a message, translated into an error of errors.py.

    Args:
        request: The request of the page that shows it.
        error: Any exception; it is translated into an error of errors/.
        prefix: A text before the title, such as "Not saved. ".

    Returns:
        The error shown.
    """
    error = errors.translate(error)
    guide = ""
    if error.guide_url():
        guide = format_html(
            ' · <a href="{}" class="alert-link">{}</a>', error.guide_url(), error.guide_title
        )
    messages.error(
        request,
        format_html(
            '{}<strong>{}</strong>: {} <a href="{}" class="alert-link">{}</a>{}',
            prefix,
            error.title,
            error,
            error.docs_url(),
            _("What to do"),
            guide,
        ),
    )
    return error
