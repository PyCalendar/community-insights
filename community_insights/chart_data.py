"""The data of the charts for Chart.js in the browser: the same charts as charts.py, interactive.

Each function has the name and the arguments of the function of charts.py that draws the same
chart as SVG, and returns what static/js/charts.js gives to Chart.js: the type, the labels and the
series with their colours, the titles of the axes, and which axis shows durations (hours). The
SVG stays for sharing and for pages without JavaScript.
"""

import statistics

from django.utils.translation import gettext

from .charts import BAR, GAP, HEAT_STOPS, HOURS, INK, KIND_COLORS, KINDS, WEEKDAYS, month_span
from .stats import histogram

# the charts of charts.py that Chart.js can draw, by their names in addresses
INTERACTIVE = (
    "query",
    "responses-pr",
    "responses-issue",
    "responses",
    "hours",
    "heatmap",
    "months",
)


def value(point) -> float:
    """The number of a point of a series: itself, or the value of a cell of the heat map.

    Args:
        point: A number, None, or a cell such as ``{"x": "08:00", "y": "Mon", "v": 3}``.

    Returns:
        The number; 0 for None.

    Examples:
        >>> value(None), value(2), value({"x": "08:00", "y": "Mon", "v": 3})
        (0, 2, 3)
    """
    if isinstance(point, dict):
        return point.get("v") or 0
    return point or 0


def config(kind: str, labels, datasets, theme: str, x: str = "", y: str = "", **more) -> dict:
    """What charts.js gives to Chart.js.

    Args:
        kind: The type of chart of Chart.js, such as ``bar``.
        labels: The labels of the x axis.
        datasets: The series, each with a label, the data and its colour.
        theme: ``light`` or ``dark``: the colours of the page the chart is on.
        x: The title of the x axis.
        y: The title of the y axis.
        **more: More, such as ``title``, ``stacked``, ``horizontal`` or ``durations`` (the axis
            whose values are hours, shown as 10min, 6h, 7d).

    Returns:
        The chart.

    Examples:
        >>> config("bar", ["a"], [{"label": "n", "data": [1]}], "light", x="who")["x"]
        'who'
    """
    return {
        "type": kind,
        "labels": list(labels),
        "datasets": datasets,
        "x": x,
        "y": y,
        "ink": INK[theme],
        "empty": not any(value(point) for d in datasets for point in d["data"]),
        **more,
    }


def response_chart(title: str, entries, classes, theme: str = "light") -> dict:
    """How many first responses of each class fall in each time, side by side.

    Args:
        title: The kind, such as *Pull requests*.
        entries: The seconds until the first response of each class, one dictionary per item.
        classes: The classes of people, in their order, with their colours.
        theme: ``light`` or ``dark``: the colours of the page the chart is on.

    Returns:
        The chart for Chart.js.
    """
    rows = histogram(entries, [c.name for c in classes])
    silent = sum(1 for e in entries if not e)
    return config(
        "bar",
        [label for label, _ in rows],
        [
            {
                "label": c.name,
                "data": [counts[c.name] for _, counts in rows],
                "backgroundColor": c.color,
                "borderColor": GAP[theme],
                "borderWidth": 1,
            }
            for c in classes
        ],
        theme,
        x=gettext("time until the first response"),
        y=gettext("responses"),
        title=gettext("%(title)s (%(items)s, %(silent)s without a response)")
        % {"title": title, "items": len(entries), "silent": silent},
    )


def query_chart(labels: list[str], values, title: str, theme: str = "light") -> dict:
    """Horizontal bars for the result of a query, the biggest on top.

    Args:
        labels: The people or groups, the biggest first.
        values: Their numbers.
        title: What the numbers are, for the axis.
        theme: ``light`` or ``dark``: the colours of the page the chart is on.

    Returns:
        The chart for Chart.js.
    """
    return config(
        "bar",
        labels,
        [{"label": title, "data": list(values), "backgroundColor": BAR[theme]}],
        theme,
        x=title,
        horizontal=True,
    )


def hour_chart(grid, theme: str = "light") -> dict:
    """The activities per hour of the day, of the 7 x 24 grid.

    Args:
        grid: The activities, a list of 7 weekdays of 24 hours each.
        theme: ``light`` or ``dark``: the colours of the page the chart is on.

    Returns:
        The chart for Chart.js.
    """
    totals = [sum(grid[day][hour] for day in range(7)) for hour in range(24)]
    return config(
        "bar",
        [f"{hour:02d}:00" for hour in range(24)],
        [{"label": gettext("activities (number)"), "data": totals, "backgroundColor": BAR[theme]}],
        theme,
        x=gettext("time of the day (your time zone)"),
        y=gettext("activities (number)"),
    )


def heatmap(grid, theme: str = "light") -> dict:
    """The activities per weekday and hour, as a heat map (chartjs-chart-matrix).

    Args:
        grid: The activities, a list of 7 weekdays (Monday first) of 24 hours each.
        theme: ``light`` or ``dark``: the colours of the page the chart is on.

    Returns:
        The chart for Chart.js: one cell per hour and weekday, with the colours from few to many.
    """
    cells = [
        {"x": f"{hour:02d}:00", "y": str(WEEKDAYS[day]), "v": grid[day][hour]}
        for day in range(7)
        for hour in range(24)
    ]
    return config(
        "matrix",
        [f"{hour:02d}:00" for hour in range(24)],
        [{"label": gettext("activities (number)"), "data": cells}],
        theme,
        x=gettext("time of the day (your time zone)"),
        y=gettext("weekday"),
        rows=[str(day) for day in WEEKDAYS],
        heat=HEAT_STOPS,
        hours=HOURS,
    )


def response_month_chart(months, theme: str = "light") -> dict:
    """The median time of a person's first responses, per month, and how many there were.

    Args:
        months: The seconds of the first responses by (year, month).
        theme: ``light`` or ``dark``: the colours of the page the chart is on.

    Returns:
        The chart for Chart.js: the median in hours per month, empty months without a point.
    """
    span = month_span(list(months)) if months else []
    return config(
        "line",
        [f"{y}-{m:02d}" for y, m in span],
        [
            {
                "label": gettext("median time until the first response"),
                "data": [
                    statistics.median(months[k]) / 3600 if months.get(k) else None for k in span
                ],
                "counts": [len(months.get(k, [])) for k in span],
                "borderColor": BAR[theme],
                "backgroundColor": BAR[theme],
                "spanGaps": True,
            }
        ],
        theme,
        y=gettext("median time until the first response"),
        durations="y",
    )


def month_chart(months, theme: str = "light") -> dict:
    """Activities per month by kind, stacked (the dict of `stats.by_month_and_kind`).

    Args:
        months: The activities by (year, month) and kind.
        theme: ``light`` or ``dark``: the colours of the page the chart is on.

    Returns:
        The chart for Chart.js.
    """
    span = month_span(list(months)) if months else []
    return config(
        "bar",
        [f"{y}-{m:02d}" for y, m in span],
        [
            {
                "label": str(KINDS.get(kind, kind)),
                "data": [months.get(key, {}).get(kind, 0) for key in span],
                "backgroundColor": color,
                "borderColor": GAP[theme],
                "borderWidth": 1,
            }
            for kind, color in KIND_COLORS[theme].items()
        ],
        theme,
        y=gettext("activities (number)"),
        stacked=True,
    )
