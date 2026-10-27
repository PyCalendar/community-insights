"""Charts drawn with matplotlib, as SVG, in the colours of the website.

Charts drawn with matplotlib, returned as SVG, in the colours of the website (static/style.css): the
green palette, for a light or a dark page.
"""

import io
from collections.abc import Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

from .stats import histogram  # noqa: E402

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
HEAT = {
    "light": LinearSegmentedColormap.from_list(
        "community-light", ["#f3faf3", GREEN_LIGHT, GREEN, GREEN_DEEPEST]
    ),
    "dark": LinearSegmentedColormap.from_list(
        "community-dark", ["#14231a", GREEN_DEEPEST, GREEN, GREEN_LIGHT]
    ),
}
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
THEMES = ("light", "dark")


def svg(figure) -> bytes:
    """The figure as SVG, with a transparent background; the figure is closed."""
    buffer = io.BytesIO()
    figure.savefig(buffer, format="svg", bbox_inches="tight", transparent=True)
    plt.close(figure)
    return buffer.getvalue()


def style(axes, theme: str, legend: bool = False):
    """The axes in the colours of the theme, with a legend if wanted."""
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
    """A small chart that only says why there is nothing to show."""
    figure, axes = plt.subplots(figsize=(6, 1.2))
    axes.axis("off")
    axes.text(0.5, 0.5, message, ha="center", va="center", color=INK[theme])
    return svg(figure)


def response_chart(title: str, entries, classes, theme: str = "light") -> bytes:
    """Stacked bars of the first responses of each class per time.

    Stacked bars: how many first responses of each class fall in each time. The classes have the
    colours chosen on the page Classes.
    """
    names = [c.name for c in classes]
    rows = histogram(entries, names)
    if not any(any(c.values()) for _, c in rows):
        return empty(f"{title}: no responses yet", theme)
    figure, axes = plt.subplots(figsize=(7, 3.2))
    bottoms = [0] * len(rows)
    for person_class in classes:
        values = [c[person_class.name] for _, c in rows]
        axes.bar(
            [label for label, _ in rows],
            values,
            bottom=bottoms,
            color=person_class.color,
            label=person_class.name,
            edgecolor=GAP[theme],
            linewidth=0.6,
        )
        bottoms = [b + v for b, v in zip(bottoms, values, strict=True)]
    silent = sum(1 for e in entries if not e)
    axes.set_title(f"{title} ({len(entries)}, {silent} without a response)")
    axes.set_xlabel("time until the first response")
    axes.set_ylabel("responses")
    style(axes, theme, legend=True)
    return svg(figure)


def query_chart(
    labels: list[str], values: Sequence[float], title: str, theme: str = "light"
) -> bytes:
    """Horizontal bars for the result of a query, the biggest on top."""
    if not labels:
        return empty("nobody matches the query", theme)
    figure, axes = plt.subplots(figsize=(7, max(1.6, 0.28 * len(labels) + 0.8)))
    axes.barh(labels[::-1], values[::-1], color=BAR[theme])
    axes.set_xlabel(title)
    style(axes, theme)
    return svg(figure)


def hour_chart(grid, theme: str = "light") -> bytes:
    """Bars of the activities per hour of the day, of the 7 x 24 grid."""
    totals = [sum(grid[day][hour] for day in range(7)) for hour in range(24)]
    figure, axes = plt.subplots(figsize=(6, 2.4))
    axes.bar(range(24), totals, color=BAR[theme])
    axes.set_xticks(range(0, 24, 3))
    axes.set_xlabel("hour of the day (your time zone)")
    axes.set_ylabel("activities")
    style(axes, theme)
    return svg(figure)


def heatmap(grid, theme: str = "light") -> bytes:
    """The activities per weekday and hour of the 7 x 24 grid, as a heat map."""
    figure, axes = plt.subplots(figsize=(7, 2.8))
    image = axes.imshow(grid, aspect="auto", cmap=HEAT[theme])
    axes.set_yticks(range(7), WEEKDAYS)
    axes.set_xticks(range(0, 24, 3))
    axes.set_xlabel("hour of the day (your time zone)")
    bar = figure.colorbar(image, ax=axes, pad=0.02)
    bar.outline.set_visible(False)
    bar.ax.tick_params(colors=INK[theme])
    style(axes, theme)
    for side in ("left", "bottom"):
        axes.spines[side].set_visible(False)
    return svg(figure)


def month_span(keys) -> list[tuple[int, int]]:
    """Every month from the first to the last of the keys."""
    (y0, m0), (y1, m1) = min(keys), max(keys)
    return [
        (y0 + (m0 - 1 + i) // 12, (m0 - 1 + i) % 12 + 1)
        for i in range((y1 - y0) * 12 + m1 - m0 + 1)
    ]


def response_month_chart(months, theme: str = "light") -> bytes:
    """The median time of a person's first responses, per month.

    The median hours until a person's first response, per month, with the number of responses as
    the size of the dots.
    """
    import statistics

    if not months:
        return empty("no responses to others", theme)
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
    axes.set_ylabel("median hours")
    axes.set_yscale("symlog", linthresh=1)
    style(axes, theme)
    return svg(figure)


def month_chart(months, theme: str = "light") -> bytes:
    """Activities per month by kind (the dict of `stats.by_month_and_kind`)."""
    if not months:
        return empty("no activity", theme)
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
            label=kind,
            edgecolor=GAP[theme],
            linewidth=0.6,
        )
        bottoms = [b + v for b, v in zip(bottoms, values, strict=True)]
    step = max(1, len(span) // 12)
    axes.set_xticks(range(0, len(span), step), labels[::step], rotation=45, ha="right")
    axes.set_ylabel("activities")
    style(axes, theme, legend=True)
    return svg(figure)
