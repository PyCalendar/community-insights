from urllib.parse import quote, urlencode

from django.http import Http404
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from .. import stats
from ..models import (
    Item,
    Person,
)
from .scope import scope_of, scope_view, stats_page

# the fits of the table of response times, in the order of the choice
FITS = ["measured", "normal", "exponential", "Kaplan-Meier"]


def fit_table(title: str, kind: str, found, names: list[str]) -> tuple:
    """A table of the response times, the fit shown first and the trend.

    Args:
        title: The title of the table.
        kind: ``pr`` or ``issue``.
        found: For each item the time it was created, its first response times and how long it
            was observed (``stats.response_rows``).
        names: The names of the classes, in their order.

    Returns:
        The title, the kind, the rows, the fit with the lowest standard error, and the trend
        (None without enough responses).
    """
    entries = [times for _, times, _ in found]
    observed = [seconds for _, _, seconds in found]
    rows = stats.summary(entries, names, observed)
    return title, kind, rows, stats.best_fit(rows), stats.trend(found)


@scope_view
def overview(request, scope):
    """The overview of a scope: counts, response time charts and tables, badges.

    Args:
        request: The request.
        scope: The text of the scope.

    Returns:
        The page.
    """
    scope = scope_of(request, scope)
    classes = scope.visible_classes()
    found = stats.response_rows(scope.repositories, scope.classifier(), scope.since, scope.until)
    names = [c.name for c in classes]
    return stats_page(
        request,
        scope,
        "community/overview.html",
        {
            "scope": scope,
            "counts": stats.counts(scope.repositories, scope.since, scope.until),
            "tables": [
                fit_table(_("Pull requests"), "pr", found[Item.PR], names),
                fit_table(_("Issues"), "issue", found[Item.ISSUE], names),
            ],
            "fits": FITS,
            "classes": classes,
            "page_url": request.build_absolute_uri(
                scope.shared(reverse("overview", args=[scope.text]))
            ),
            "badge_url": request.build_absolute_uri(
                (
                    reverse("public_badge", args=[scope.text])
                    if scope.public
                    else reverse("badge", args=[scope.projects[0].badge_token])
                )
                # the classes of the page, when they are not the default ones
                + ("?" + urlencode(scope.carried) if scope.carried else "")
            ),
        },
    )


@scope_view
def person(request, scope, login):
    """What one person did: numbers, contributions per month, when they are active.

    Args:
        request: The request.
        scope: The text of the scope.
        login: The handle of the person.

    Returns:
        The page.

    Raises:
        Http404: If the person did nothing in the repositories.
    """
    scope = scope_of(request, scope)
    if not stats.activity_of(scope.repositories, login):
        raise Http404("No activity")
    people = [
        p for p in scope.contributors(classified=False) if p.login.lower() == login.lower()
    ] or [stats.Contributor(login)]  # nothing in the time range
    Person.touch_all(Person.objects.filter(login__iexact=login))
    return stats_page(
        request,
        scope,
        "community/person.html",
        {
            "scope": scope,
            "person": people[0],
            "login": login,
            "login_q": quote(login),
            "timezone": timezone.get_current_timezone_name(),
        },
    )
