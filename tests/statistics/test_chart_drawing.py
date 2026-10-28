"""How the charts are drawn: bars side by side, readable axes, a heat map without white."""

from types import SimpleNamespace

import pytest
from matplotlib.colors import to_hex, to_rgb

from community_insights import charts


@pytest.fixture
def figures(monkeypatch):
    """The figures drawn, instead of their SVG."""
    drawn = []

    def keep(figure):
        """Keep the figure instead of saving it."""
        drawn.append(figure)
        return b"<svg/>"

    monkeypatch.setattr(charts, "svg", keep)
    return drawn


CLASSES = [
    SimpleNamespace(name="maintainer", color="#2b5329"),
    SimpleNamespace(name="bot", color="#9ccc9c"),
]


def test_the_classes_are_side_by_side(figures):
    """The classes are side by side."""
    entries = [{"maintainer": 60.0, "bot": 30.0}, {"maintainer": 60.0}, {}]
    charts.response_chart("Pull requests", entries, CLASSES)
    axes = figures[0].axes[0]
    bars = {
        (round(p.get_x(), 3), p.get_y(), p.get_height()) for p in axes.patches if p.get_height()
    }
    assert len(bars) == 2
    (left, y1, maintainers), (right, y2, bots) = sorted(bars)
    assert y1 == y2 == 0, "not stacked"
    assert (maintainers, bots) == (2, 1)
    assert left < right
    labels = [t.get_text() for t in axes.get_xticklabels()]
    assert labels[0] == "1h" and labels[-1] == "> 3w"


def test_the_response_times_per_month_show_durations_from_zero(figures):
    """The response times per month show durations from zero."""
    months = {(2026, 1): [30.0], (2026, 2): [3 * 3600.0], (2026, 4): [2 * 86400.0]}
    charts.response_month_chart(months)
    axes = figures[0].axes[0]
    figures[0].canvas.draw()
    labels = [t.get_text() for t in axes.get_yticklabels()]
    assert labels[0] == "0" and "1h" in labels and "1d" in labels and "7d" in labels
    assert not any("10^" in label or "$" in label for label in labels), "no powers of ten"
    assert axes.get_ylim()[0] == 0
    assert "first response" in axes.get_ylabel()


def test_short_response_times_have_a_scale_too(figures):
    """Short response times have a scale too."""
    charts.response_month_chart({(2026, 1): [5.0, 20.0]})
    axes = figures[0].axes[0]
    figures[0].canvas.draw()
    labels = [t.get_text() for t in axes.get_yticklabels()]
    assert labels == ["0", "1min"]


def test_the_day_and_the_week_have_units(figures):
    """The day and the week have units."""
    grid = [[(day + hour) % 5 for hour in range(24)] for day in range(7)]
    charts.hour_chart(grid)
    charts.heatmap(grid)
    hours, heat = figures[0].axes[0], figures[1].axes[0]
    for axes in (hours, heat):
        assert [t.get_text() for t in axes.get_xticklabels()][:2] == ["00:00", "03:00"]
        assert "time of the day" in axes.get_xlabel()
    assert hours.get_ylabel() == "activities (number)"
    assert heat.get_ylabel() == "weekday"
    assert figures[1].axes[1].get_ylabel() == "activities (number)", "the scale of the colours"


@pytest.mark.parametrize("theme", charts.THEMES)
def test_the_heat_map_goes_from_dark_to_the_full_green(theme):
    """The heat map goes from dark to the full green."""
    colors = charts.HEAT[theme]
    darkest, fullest = to_rgb(colors(0.0)), to_rgb(colors(1.0))
    assert sum(darkest) / 3 < 0.25, "few is dark, not white"
    assert to_hex(fullest) == charts.GREEN
    assert all(sum(to_rgb(colors(x / 10))) / 3 < 0.6 for x in range(11)), "no white at all"


def test_the_survival_chart_draws_a_step_curve_with_a_band_per_class(figures):
    """Each class with a response gets a falling step curve and its confidence band."""
    entries = [{"maintainer": 60.0}, {"maintainer": 3600.0, "bot": 5.0}, {}]
    charts.survival_chart("Pull requests", entries, [60.0, 3600.0, 86400.0], CLASSES)
    axes = figures[0].axes[0]
    lines = axes.get_lines()
    assert [line.get_label() for line in lines] == ["maintainer", "bot"]
    assert [to_hex(line.get_color()) for line in lines] == ["#2b5329", "#9ccc9c"]
    shares = lines[0].get_ydata()
    assert shares[0] == 100 and min(shares) < 100, "from all waiting, down at each response"
    assert len(axes.collections) == 2, "a confidence band per class"
    assert axes.get_xscale() == "symlog"
    assert axes.get_ylim() == (0, 100)


def test_the_survival_chart_without_responses_says_so():
    """No class got a response: the chart says so."""
    svg = charts.survival_chart("Issues", [{}, {}], [10.0, 20.0], CLASSES).decode()
    assert "Issues: no responses yet" in svg
