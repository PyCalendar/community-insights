from urllib.parse import urlencode

from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache

from .. import chart_data, charts, query, stats
from ..models import (
    Item,
)
from .contributors import CHART_TOP, query_parameters, run_query
from .scope import scope_of, scope_view

# the charts and what they show, for the page to share them
CHARTS = {
    "query": _("chart of the query"),
    "responses-pr": _("first response times of pull requests"),
    "responses-issue": _("first response times of issues"),
    "survival-pr": _("pull requests still waiting for a response"),
    "survival-issue": _("issues still waiting for a response"),
    "responses": _("how fast they respond to others, per month"),
    "hours": _("activities across the day"),
    "heatmap": _("activities across the week and the day"),
    "months": _("contributions per month"),
}


def draw(request, scope, name, drawing):
    """A chart of a scope, drawn by charts.py (SVG) or chart_data.py (data for Chart.js).

    Args:
        request: The request, with ``theme``, ``login`` or the query of the chart.
        scope: The text of the scope.
        name: The chart, such as ``responses-pr``.
        drawing: The module that draws: ``charts`` or ``chart_data``.

    Returns:
        What the module drew.

    Raises:
        Http404: If there is no chart of this name.
    """
    scope = scope_of(request, scope)
    tz = timezone.get_current_timezone()
    theme = request.GET.get("theme") if request.GET.get("theme") in charts.THEMES else "light"
    classes = scope.visible_classes()
    if name == "query":
        parameters = query_parameters(request)
        result = run_query(scope, parameters)
        measure = parameters["chart"] if parameters["chart"] in query.NUMBERS else "activity_total"
        if result.groups:
            labels = [label for label, _, _ in result.groups][:CHART_TOP]
            values = [sums[measure] for _, _, sums in result.groups][:CHART_TOP]
        else:
            top = result.contributors[:CHART_TOP]
            labels = [c.login for c in top]
            values = [query.value(c, measure, timezone.now()) for c in top]
            values = [0 if v == float("inf") else v for v in values]
        data = drawing.query_chart(labels, values, str(query.VARIABLES[measure][0]), theme)
    elif name in ("responses-pr", "responses-issue"):
        kind = name.removeprefix("responses-")
        entries = stats.response_entries(
            scope.repositories, scope.classifier(), scope.since, scope.until
        )[kind]
        title = gettext("Pull requests") if kind == Item.PR else gettext("Issues")
        data = drawing.response_chart(title, entries, classes, theme)
    elif name in ("survival-pr", "survival-issue"):
        kind = name.removeprefix("survival-")
        entries, observed = stats.response_times(
            scope.repositories, scope.classifier(), scope.since, scope.until
        )
        title = gettext("Pull requests") if kind == Item.PR else gettext("Issues")
        data = drawing.survival_chart(title, entries[kind], observed[kind], classes, theme)
    elif name == "responses":
        months = stats.responses_by_month(
            scope.repositories, request.GET.get("login", ""), tz, scope.since, scope.until
        )
        data = drawing.response_month_chart(months, theme)
    elif name in ("hours", "heatmap", "months"):
        activity = stats.activity_of(
            scope.repositories, request.GET.get("login", ""), scope.since, scope.until
        )
        if name == "months":
            data = drawing.month_chart(stats.by_month_and_kind(activity, tz), theme)
        else:
            grid = stats.by_hour_and_weekday([t for t, _ in activity], tz)
            data = (
                drawing.hour_chart(grid, theme) if name == "hours" else drawing.heatmap(grid, theme)
            )
    else:
        raise Http404
    return data


@scope_view
@never_cache
def chart(request, scope, name):
    """A chart as SVG; ?theme=dark for a dark page.

    Args:
        request: The request, with ``theme``, ``login`` or the query of the chart.
        scope: The text of the scope.
        name: The chart, such as ``responses-pr``.

    Returns:
        The SVG.
    """
    return HttpResponse(draw(request, scope, name, charts), content_type="image/svg+xml")


@scope_view
@never_cache
def chart_json(request, scope, name):
    """The data of a chart for Chart.js (static/js/charts.js); ?theme=dark for a dark page.

    Args:
        request: The request, with ``theme``, ``login`` or the query of the chart.
        scope: The text of the scope.
        name: The chart, one of ``chart_data.INTERACTIVE``.

    Returns:
        The chart as JSON.

    Raises:
        Http404: If the chart has no interactive version.
    """
    if name not in chart_data.INTERACTIVE:
        raise Http404("No interactive chart of this name")
    return JsonResponse(draw(request, scope, name, chart_data))


@scope_view
def chart_share(request, scope, name):
    """The page to share a chart: its code for Markdown, reStructuredText, HTML and its address.

    The code links the chart to the page it was shown on (the parameter ``from``), so people who
    see it find where it comes from.

    Args:
        request: The request, with the parameters of the chart and ``from``.
        scope: The text of the scope.
        name: The chart.

    Returns:
        The page.

    Raises:
        Http404: If there is no chart of this name.
    """
    scope = scope_of(request, scope)
    if name not in CHARTS:
        raise Http404("No such chart")
    parameters = [
        (key, value)
        for key, values in request.GET.lists()
        if key not in ("from", "theme")
        for value in values
    ]
    image = reverse("chart", args=[scope.text, name])
    if parameters:
        image += "?" + urlencode(parameters)
    page = request.GET.get("from", "")
    if not page.startswith("/") or not url_has_allowed_host_and_scheme(
        page, allowed_hosts={request.get_host()}
    ):
        page = reverse("overview", args=[scope.text]) + scope.query
    alt = f"{scope.title}: {CHARTS[name]}"
    if request.GET.get("login"):
        alt += f" ({request.GET['login']})"
    return render(
        request,
        "community/share.html",
        {
            "scope": scope,
            "image": request.build_absolute_uri(image),
            "preview": image,  # the page loads it from this site
            "page": request.build_absolute_uri(page),
            "alt": alt,
        },
    )
