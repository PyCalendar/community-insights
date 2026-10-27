from urllib.parse import quote

from django.http import Http404
from django.urls import reverse
from django.utils import timezone

from .. import stats
from ..classify import class_list
from ..models import (
    Item,
    Person,
)
from .scope import scope_of, scope_view, stats_page


@scope_view
def overview(request, scope):
    """The overview of a scope: counts, response time charts and tables, badges."""
    scope = scope_of(request, scope)
    classes = class_list(request.user)
    entries, observed = stats.response_times(
        scope.repositories, scope.classifier(), scope.since, scope.until
    )
    names = [c.name for c in classes]
    return stats_page(
        request,
        scope,
        "community/overview.html",
        {
            "scope": scope,
            "counts": stats.counts(scope.repositories, scope.since, scope.until),
            "tables": [
                (
                    "Pull requests",
                    "pr",
                    stats.summary(entries[Item.PR], names, observed[Item.PR]),
                ),
                (
                    "Issues",
                    "issue",
                    stats.summary(entries[Item.ISSUE], names, observed[Item.ISSUE]),
                ),
            ],
            "classes": classes,
            "badge_url": request.build_absolute_uri(
                reverse("public_badge", args=[scope.text])
                if scope.public
                else reverse("badge", args=[scope.projects[0].badge_token])
            ),
        },
    )


@scope_view
def person(request, scope, login):
    """What one person did: numbers, contributions per month, when they are active."""
    scope = scope_of(request, scope)
    if not stats.activity_of(scope.repositories, login):
        raise Http404("No activity")
    people = [
        p
        for p in stats.contributors(scope.repositories, since=scope.since, until=scope.until)
        if p.login.lower() == login.lower()
    ] or [stats.Contributor(login)]  # nothing in the time range
    Person.objects.filter(login__iexact=login).update(last_used_at=timezone.now())
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
