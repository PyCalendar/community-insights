from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render

from .. import licenses
from .explore import explore


def home(request):
    """The start page: the dashboard when signed in, else Explore.

    Args:
        request: The request.

    Returns:
        A redirect to the dashboard, or the page Explore.
    """
    if request.user.is_authenticated:
        return redirect("dashboard")
    return explore(request)


def about(request):
    """The About page: what is stored, the version and the licenses.

    Args:
        request: The request.

    Returns:
        The page.
    """
    return render(
        request,
        "community/about.html",
        {
            "packages": licenses.packages(),
            "scripts": licenses.scripts(),
            "reused": licenses.reused(),
        },
    )


def license_text(request, name):
    """The text of the license of an installed Python package, as plain text.

    Args:
        request: The request.
        name: The name of the package.

    Returns:
        The text.

    Raises:
        Http404: If the package is not installed or ships no license file.
    """
    text = licenses.license_text(name)
    if text is None:
        raise Http404(name)
    return HttpResponse(text, content_type="text/plain; charset=utf-8")
