from urllib.parse import urlencode

from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from .. import chart_data, charts, query, stats
from ..models import (
    Item,
)
from .contributors import CHART_TOP, query_parameters, run_query
from .scope import scope_of, scope_view
from .stamped import stamped
from .statistics import bars_of

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
    "trend-pr": _("pull requests opened, closed and merged"),
    "trend-issue": _("issues opened and closed"),
    "people-pr": _("contributions and new contributors to pull requests"),
    "people-issue": _("contributions and new contributors to issues"),
    "reviews-time": _("reviews by collaborators and by others over time"),
    "reviews-kinds": _("the kinds of review by collaborators and by others"),
    "reviews-merge": _("the reviews of pull requests until they were merged"),
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
    elif name in ("trend-pr", "trend-issue", "people-pr", "people-issue"):
        data = trend_chart(scope, name, drawing, theme, bars_of(request))
    elif name in ("reviews-time", "reviews-kinds", "reviews-merge"):
        data = review_chart(scope, name, drawing, theme, bars_of(request))
    else:
        raise Http404
    return data


def trend_chart(scope, name: str, drawing, theme: str, by: str = ""):
    """A chart of the page Trends: opened and closed, or contributions and new contributors.

    Args:
        scope: The scope, with its time range.
        name: ``trend-pr``, ``trend-issue``, ``people-pr`` or ``people-issue``.
        drawing: The module that draws: ``charts`` or ``chart_data``.
        theme: ``light`` or ``dark``.
        by: The length of the bars, "" to choose it by the time range.

    Returns:
        What the module drew.
    """
    part, kind = name.split("-")
    found = stats.kind_series(
        scope.repositories,
        kind,
        scope.since,
        scope.until,
        timezone.now(),
        timezone.get_current_timezone(),
        by,
    )
    if part == "trend":
        title = gettext("Pull requests") if kind == Item.PR else gettext("Issues")
        series = [(gettext("opened"), found["opened"]), (gettext("closed"), found["closed"])]
        if kind == Item.PR:  # closed without merging, and merged
            series = [
                (gettext("opened"), found["opened"]),
                (gettext("closed without merging"), found["closed"]),
                (gettext("merged"), found["merged"]),
            ]
    else:
        title = (
            gettext("Contributions to pull requests")
            if kind == Item.PR
            else gettext("Contributions to issues")
        )
        series = [
            (gettext("contributions"), found["contributions"]),
            (gettext("new contributors"), found["newcomers"]),
        ]
    return drawing.pair_chart(title, found["labels"], series, found["size"], theme)


def review_chart(scope, name: str, drawing, theme: str, by: str = ""):
    """A chart of the page Reviews: over time, by kind, or until merged.

    Args:
        scope: The scope, with its time range.
        name: ``reviews-time``, ``reviews-kinds`` or ``reviews-merge``.
        drawing: The module that draws: ``charts`` or ``chart_data``.
        theme: ``light`` or ``dark``.
        by: The length of the bars over time, "" to choose it by the time range.

    Returns:
        What the module drew.
    """
    who = [gettext("by collaborators"), gettext("by others")]
    if name == "reviews-time":
        found = stats.review_series(
            scope.repositories,
            scope.since,
            scope.until,
            timezone.now(),
            timezone.get_current_timezone(),
            by,
        )
        series = [(who[0], found["collaborators"]), (who[1], found["others"])]
        return drawing.pair_chart(gettext("Reviews"), found["labels"], series, found["size"], theme)
    numbers = stats.review_numbers(scope.repositories, scope.since, scope.until, timezone.now())
    if name == "reviews-kinds":
        labels = [str(REVIEW_KINDS[kind]) for kind in numbers.kinds]
        series = [
            (who[0], [pair[0] for pair in numbers.kinds.values()]),
            (who[1], [pair[1] for pair in numbers.kinds.values()]),
        ]
        return drawing.pair_chart(
            gettext("Kinds of review"), labels, series, gettext("kind of review"), theme
        )
    labels = [str(n) for n in range(len(numbers.histogram) - 1)]
    labels.append(f"{len(numbers.histogram) - 1}+")
    return drawing.pair_chart(
        gettext("Reviews until merged"),
        labels,
        [(gettext("merged pull requests"), numbers.histogram)],
        gettext("reviews before the merge"),
        theme,
    )


# the names of the kinds of review (stats.review_numbers.KINDS)
REVIEW_KINDS = {
    "approved": _("approved"),
    "changes_requested": _("changes requested"),
    "commented": _("commented"),
    "other": _("dismissed or unknown"),
}


@scope_view
@stamped
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
@stamped
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
    see it find where it comes from. Both addresses open without a sign in (``Scope.shared``):
    a project is shown as its public repositories, with the time range and the classes.

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
    back = request.GET.get("from", "")
    if not back.startswith("/") or not url_has_allowed_host_and_scheme(
        back, allowed_hosts={request.get_host()}
    ):
        back = reverse("overview", args=[scope.text]) + scope.query
    # what is shared opens without a sign in: the public repositories, the range, the classes
    shared = scope.shared(image)
    page = scope.shared(back)
    alt = f"{scope.title}: {CHARTS[name]}"
    if request.GET.get("login"):
        alt += f" ({request.GET['login']})"
    return render(
        request,
        "community/share.html",
        {
            "scope": scope,
            "image": request.build_absolute_uri(shared),
            "preview": shared,  # the page loads it from this site
            "page": request.build_absolute_uri(page),
            "back": back,
            "alt": alt,
        },
    )
