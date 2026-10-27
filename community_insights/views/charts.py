from django.http import Http404, HttpResponse
from django.utils import timezone
from django.views.decorators.cache import never_cache

from .. import charts, query, stats
from ..classify import class_list
from ..models import (
    Item,
)
from .contributors import CHART_TOP, query_parameters, run_query
from .scope import scope_of, scope_view


@scope_view
@never_cache
def chart(request, scope, name):
    """A chart as SVG; ?theme=dark for a dark page."""
    scope = scope_of(request, scope)
    tz = timezone.get_current_timezone()
    theme = request.GET.get("theme") if request.GET.get("theme") in charts.THEMES else "light"
    classes = class_list(request.user)
    if name == "query":
        parameters = query_parameters(request)
        result = run_query(scope, parameters)
        measure = parameters["chart"] if parameters["chart"] in query.NUMBERS else "activity"
        if result.groups:
            labels = [label for label, _, _ in result.groups][:CHART_TOP]
            values = [sums[measure] for _, _, sums in result.groups][:CHART_TOP]
        else:
            top = result.contributors[:CHART_TOP]
            labels = [c.login for c in top]
            values = [query.value(c, measure, timezone.now()) for c in top]
            values = [0 if v == float("inf") else v for v in values]
        data = charts.query_chart(labels, values, query.VARIABLES[measure][0], theme)
    elif name in ("responses-pr", "responses-issue"):
        kind = name.removeprefix("responses-")
        entries = stats.response_entries(
            scope.repositories, scope.classifier(), scope.since, scope.until
        )[kind]
        title = "Pull requests" if kind == Item.PR else "Issues"
        data = charts.response_chart(title, entries, classes, theme)
    elif name == "responses":
        months = stats.responses_by_month(
            scope.repositories, request.GET.get("login", ""), tz, scope.since, scope.until
        )
        data = charts.response_month_chart(months, theme)
    elif name in ("hours", "heatmap", "months"):
        activity = stats.activity_of(
            scope.repositories, request.GET.get("login", ""), scope.since, scope.until
        )
        if name == "months":
            data = charts.month_chart(stats.by_month_and_kind(activity, tz), theme)
        else:
            grid = stats.by_hour_and_weekday([t for t, _ in activity], tz)
            data = (
                charts.hour_chart(grid, theme) if name == "hours" else charts.heatmap(grid, theme)
            )
    else:
        raise Http404
    return HttpResponse(data, content_type="image/svg+xml")
