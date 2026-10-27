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
