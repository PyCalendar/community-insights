"""Charts drawn with matplotlib, as SVG, in the colours of the website.

Charts drawn with matplotlib, returned as SVG, in the colours of the website (static/style.css): the
green palette, for a light or a dark page.
"""

import io
from collections.abc import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from django.utils.translation import gettext, gettext_lazy  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.ticker import FixedLocator, FuncFormatter  # noqa: E402

from .stats import format_duration, histogram, survival  # noqa: E402

plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["font.size"] = 9

# the palette of static/style.css
GREEN = "#149414"
GREEN_DARK = "#0e6b0e"
GREEN_MUTED = "#649568"
GREEN_LIGHT = "#9ccc9c"
GREEN_DEEPEST = "#2b5329"

# text and lines: --text-muted of the light and the dark page
INK = {"light": "#4d5f4d", "dark": "#a9bfa9"}
# between stacked bars, so series that are close in colour stay apart
GAP = {"light": "#ffffff", "dark": "#101a10"}
# series told apart by lightness, darkest first
KIND_COLORS = {
    "light": {
        "pull request": GREEN_DEEPEST,
        "issue": GREEN,
        "comment": GREEN_MUTED,
        "review": GREEN_LIGHT,
        "commit": "#8fa58f",
    },
    "dark": {
        "pull request": GREEN_LIGHT,
        "issue": GREEN,
        "comment": GREEN_MUTED,
        "review": GREEN_DEEPEST,
        "commit": "#4f6b4f",
    },
}
BAR = {"light": GREEN_DARK, "dark": GREEN_LIGHT}
# from dark (few) to the full green (many): no white, which looked like missing data
HEAT_STOPS = ["#1c331b", GREEN_DEEPEST, GREEN_DARK, GREEN]
HEAT = {
    theme: LinearSegmentedColormap.from_list(f"community-{theme}", HEAT_STOPS)
    for theme in ("light", "dark")
}
WEEKDAYS = [
    gettext_lazy("Mon"),
    gettext_lazy("Tue"),
    gettext_lazy("Wed"),
    gettext_lazy("Thu"),
    gettext_lazy("Fri"),
    gettext_lazy("Sat"),
    gettext_lazy("Sun"),
]
# the kinds of activity in the legend, by the key of stats.by_month_and_kind
KINDS = {
    "pull request": gettext_lazy("pull request"),
    "issue": gettext_lazy("issue"),
    "comment": gettext_lazy("comment"),
    "review": gettext_lazy("review"),
    "commit": gettext_lazy("commit"),
}
HOURS = [f"{hour:02d}:00" for hour in range(0, 24, 3)]
# the marks of a time axis, in hours: from a minute to a year
DURATION_TICKS = [0, 1 / 60, 10 / 60, 1, 6, 24, 24 * 7, 24 * 30, 24 * 365]
THEMES = ("light", "dark")


def svg(figure) -> bytes:
    """The figure as SVG, with a transparent background; the figure is closed.

    Args:
        figure: A figure of matplotlib.

    Returns:
        The SVG.
    """
    buffer = io.BytesIO()
    figure.savefig(buffer, format="svg", bbox_inches="tight", transparent=True)
    plt.close(figure)
    return buffer.getvalue()


def style(axes, theme: str, legend: bool = False):
    """The axes in the colours of the theme, with a legend if wanted.

    Args:
        axes: The axes of matplotlib.
        theme: ``light`` or ``dark``: the colours of the page the chart is on.
        legend: Whether to show the legend of the series.
    """
    ink = INK[theme]
    for side in ("top", "right"):
        axes.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        axes.spines[side].set_color(ink)
    axes.tick_params(colors=ink)
    axes.xaxis.label.set_color(ink)
    axes.yaxis.label.set_color(ink)
    axes.title.set_color(ink)
    if legend:
        for text in axes.legend(frameon=False, fontsize=8).get_texts():
            text.set_color(ink)


def empty(message: str, theme: str = "light") -> bytes:
    """A small chart that only says why there is nothing to show.

    Args:
        message: Why there is nothing to show.
        theme: ``light`` or ``dark``: the colours of the page the chart is on.

    Returns:
        The SVG.
    """
    figure, axes = plt.subplots(figsize=(6, 1.2))
    axes.axis("off")
    axes.text(0.5, 0.5, message, ha="center", va="center", color=INK[theme])
    return svg(figure)


def response_chart(title: str, entries, classes, theme: str = "light") -> bytes:
    """Bars side by side of the first responses of each class per time.

    For each time, one bar per class: how many first responses of the class fall in that time.
    The classes have the colours chosen on the page Classes.

    Args:
        title: The kind, such as *Pull requests*.
        entries: The seconds until the first response of each class, one dictionary per item.
        classes: The classes of people, in their order, with their colours.
        theme: ``light`` or ``dark``: the colours of the page the chart is on.

    Returns:
        The SVG; a chart that says so without responses.
    """
    names = [c.name for c in classes]
    rows = histogram(entries, names)
    if not any(any(c.values()) for _, c in rows):
        return empty(gettext("%(title)s: no responses yet") % {"title": title}, theme)
    figure, axes = plt.subplots(figsize=(7, 3.2))
    width = 0.8 / max(1, len(classes))
    for index, person_class in enumerate(classes):
        offset = (index - (len(classes) - 1) / 2) * width
        axes.bar(
            [position + offset for position in range(len(rows))],
            [c[person_class.name] for _, c in rows],
            width=width,
            color=person_class.color,
            label=person_class.name,
            edgecolor=GAP[theme],
            linewidth=0.6,
        )
    axes.set_xticks(range(len(rows)), [label for label, _ in rows])
    silent = sum(1 for e in entries if not e)
    axes.set_title(
        gettext("%(title)s (%(items)s, %(silent)s without a response)")
        % {"title": title, "items": len(entries), "silent": silent}
    )
    axes.set_xlabel(gettext("time until the first response"))
    axes.set_ylabel(gettext("responses"))
    style(axes, theme, legend=True)
    return svg(figure)


def query_chart(
    labels: list[str], values: Sequence[float], title: str, theme: str = "light"
) -> bytes:
    """Horizontal bars for the result of a query, the biggest on top.

    Args:
        labels: The people or groups, the biggest first.
        values: Their numbers.
        title: What the numbers are, for the axis.
        theme: ``light`` or ``dark``: the colours of the page the chart is on.

    Returns:
        The SVG; a chart that says so when nobody matches.
    """
    if not labels:
        return empty(gettext("nobody matches the query"), theme)
    figure, axes = plt.subplots(figsize=(7, max(1.6, 0.28 * len(labels) + 0.8)))
    axes.barh(labels[::-1], values[::-1], color=BAR[theme])
    axes.set_xlabel(title)
    style(axes, theme)
    return svg(figure)


def hour_chart(grid, theme: str = "light") -> bytes:
    """Bars of the activities per hour of the day, of the 7 x 24 grid.

    Args:
        grid: The activities, a list of 7 weekdays of 24 hours each.
        theme: ``light`` or ``dark``: the colours of the page the chart is on.

    Returns:
        The SVG.
    """
    totals = [sum(grid[day][hour] for day in range(7)) for hour in range(24)]
    figure, axes = plt.subplots(figsize=(6, 2.4))
    axes.bar(range(24), totals, color=BAR[theme])
    axes.set_xticks(range(0, 24, 3), HOURS)
    axes.set_xlabel(gettext("time of the day (your time zone)"))
    axes.set_ylabel(gettext("activities (number)"))
    style(axes, theme)
    return svg(figure)


def heatmap(grid, theme: str = "light") -> bytes:
    """The activities per weekday and hour of the 7 x 24 grid, as a heat map.

    Args:
        grid: The activities, a list of 7 weekdays (Monday first) of 24 hours each.
        theme: ``light`` or ``dark``: the colours of the page the chart is on.

    Returns:
        The SVG.
    """
    figure, axes = plt.subplots(figsize=(7, 2.8))
    image = axes.imshow(grid, aspect="auto", cmap=HEAT[theme])
    axes.set_yticks(range(7), [str(day) for day in WEEKDAYS])
    axes.set_xticks(range(0, 24, 3), HOURS)
    axes.set_xlabel(gettext("time of the day (your time zone)"))
    axes.set_ylabel(gettext("weekday"))
    bar = figure.colorbar(image, ax=axes, pad=0.02)
    bar.outline.set_visible(False)
    bar.ax.tick_params(colors=INK[theme])
    bar.set_label(gettext("activities (number)"), color=INK[theme])
    style(axes, theme)
    for side in ("left", "bottom"):
        axes.spines[side].set_visible(False)
    return svg(figure)


def month_span(keys) -> list[tuple[int, int]]:
    """Every month from the first to the last of the keys.

    Args:
        keys: Months as (year, month).

    Returns:
        The months as (year, month), without a gap.
    """
    (y0, m0), (y1, m1) = min(keys), max(keys)
    return [
        (y0 + (m0 - 1 + i) // 12, (m0 - 1 + i) % 12 + 1)
        for i in range((y1 - y0) * 12 + m1 - m0 + 1)
    ]


def response_month_chart(months, theme: str = "light") -> bytes:
    """The median time of a person's first responses, per month.

    The median hours until a person's first response, per month, with the number of responses as
    the size of the dots.

    Args:
        months: The seconds of the first responses by (year, month).
        theme: ``light`` or ``dark``: the colours of the page the chart is on.

    Returns:
        The SVG; a chart that says so without responses.
    """
    import statistics

    if not months:
        return empty(gettext("no responses to others"), theme)
    span = month_span(list(months))
    labels = [f"{y}-{m:02d}" for y, m in span]
    medians = [statistics.median(months[k]) / 3600 if months.get(k) else None for k in span]
    counts = [len(months.get(k, [])) for k in span]
    figure, axes = plt.subplots(figsize=(7, 2.6))
    shown = [
        (i, v, c) for i, (v, c) in enumerate(zip(medians, counts, strict=True)) if v is not None
    ]
    axes.plot([i for i, _, _ in shown], [v for _, v, _ in shown], color=BAR[theme], linewidth=1)
    axes.scatter(
        [i for i, _, _ in shown],
        [v for _, v, _ in shown],
        s=[12 + 6 * c for _, _, c in shown],
        color=BAR[theme],
        zorder=3,
    )
    step = max(1, len(span) // 12)
    axes.set_xticks(range(0, len(span), step), labels[::step], rotation=45, ha="right")
    axes.set_ylabel(gettext("median time until the first response"))
    duration_axis(axes, max(v for _, v, _ in shown))
    style(axes, theme)
    return svg(figure)


def duration_axis(axes, highest: float, axis: str = "y"):
    """An axis of hours that shows durations, such as 10min, 6h, 7d, from 0.

    Args:
        axes: The axes to change.
        highest: The highest value shown, in hours.
        axis: ``y`` or ``x``.
    """
    above = [tick for tick in DURATION_TICKS if tick >= highest]
    top = above[0] if above else highest
    shown = axes.yaxis if axis == "y" else axes.xaxis
    if axis == "y":
        axes.set_yscale("symlog", linthresh=1 / 60)
        axes.set_ylim(0, top * 1.05 or 1)
    else:
        axes.set_xscale("symlog", linthresh=1 / 60)
        axes.set_xlim(0, top * 1.05 or 1)
    shown.set_major_locator(FixedLocator([t for t in DURATION_TICKS if t <= top]))
    shown.set_minor_locator(FixedLocator([]))
    shown.set_major_formatter(
        FuncFormatter(lambda hours, _: format_duration(hours * 3600) if hours else "0")
    )


def survival_chart(title: str, entries, observed, classes, theme: str = "light") -> bytes:
    """The share of the items still waiting for a response of each class, over time.

    Kaplan-Meier curves of lifelines, with their 95 % confidence interval as a band: the items
    without a response count as waiting as long as they were observed.

    Args:
        title: The kind, such as *Pull requests*.
        entries: The seconds until the first response of each class, one dictionary per item.
        observed: How long each item was observed.
        classes: The classes of people, in their order, with their colours.
        theme: ``light`` or ``dark``: the colours of the page the chart is on.

    Returns:
        The SVG; a chart that says so without responses.
    """
    curves = [(c, survival(entries, observed, c.name)) for c in classes]
    curves = [(c, fitted) for c, fitted in curves if fitted is not None]
    if not curves:
        return empty(gettext("%(title)s: no responses yet") % {"title": title}, theme)
    figure, axes = plt.subplots(figsize=(7, 3.2))
    highest = 0.0
    for person_class, fitted in curves:
        hours = fitted.survival_function_.index.to_numpy() / 3600
        share = fitted.survival_function_.iloc[:, 0].to_numpy() * 100
        band = fitted.confidence_interval_survival_function_.to_numpy() * 100
        axes.step(hours, share, where="post", color=person_class.color, label=person_class.name)
        axes.fill_between(
            hours, band[:, 0], band[:, 1], step="post", color=person_class.color, alpha=0.15
        )
        highest = max(highest, float(hours.max()))
    duration_axis(axes, highest, "x")
    axes.set_ylim(0, 100)
    axes.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:.0f} %"))
    axes.set_title(
        gettext("%(title)s (%(items)s): still waiting for a response")
        % {"title": title, "items": len(entries)}
    )
    axes.set_xlabel(gettext("time since opened"))
    axes.set_ylabel(gettext("without a response"))
    style(axes, theme, legend=True)
    return svg(figure)


def month_chart(months, theme: str = "light") -> bytes:
    """Activities per month by kind (the dict of `stats.by_month_and_kind`).

    Args:
        months: The activities by (year, month) and kind.
        theme: ``light`` or ``dark``: the colours of the page the chart is on.

    Returns:
        The SVG; a chart that says so without activity.
    """
    if not months:
        return empty(gettext("no activity"), theme)
    keys = sorted(months)
    # every month between the first and the last, also those without activity
    (y0, m0), (y1, m1) = keys[0], keys[-1]
    span = [
        (y0 + (m0 - 1 + i) // 12, (m0 - 1 + i) % 12 + 1)
        for i in range((y1 - y0) * 12 + m1 - m0 + 1)
    ]
    figure, axes = plt.subplots(figsize=(7, 2.8))
    bottoms = [0] * len(span)
    labels = [f"{y}-{m:02d}" for y, m in span]
    for kind, color in KIND_COLORS[theme].items():
        values = [months.get(key, {}).get(kind, 0) for key in span]
        axes.bar(
            labels,
            values,
            bottom=bottoms,
            color=color,
            label=str(KINDS.get(kind, kind)),
            edgecolor=GAP[theme],
            linewidth=0.6,
        )
        bottoms = [b + v for b, v in zip(bottoms, values, strict=True)]
    step = max(1, len(span) // 12)
    axes.set_xticks(range(0, len(span), step), labels[::step], rotation=45, ha="right")
    axes.set_ylabel(gettext("activities (number)"))
    style(axes, theme, legend=True)
    return svg(figure)
