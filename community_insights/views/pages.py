from django.shortcuts import redirect, render

from .. import licenses
from .explore import explore


def home(request):
    """The start page: the dashboard when signed in, else Explore."""
    if request.user.is_authenticated:
        return redirect("dashboard")
    return explore(request)


def about(request):
    """The About page: what is stored, the version and the licenses."""
    return render(
        request,
        "community/about.html",
        {"packages": licenses.packages(), "scripts": licenses.scripts()},
    )
