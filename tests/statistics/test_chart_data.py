"""The data of the interactive charts: the same charts as the SVG, for Chart.js."""

from types import SimpleNamespace

import pytest

from community_insights import chart_data, charts

CLASSES = [
    SimpleNamespace(name="maintainer", color="#2b5329"),
    SimpleNamespace(name="bot", color="#9ccc9c"),
]


def test_every_interactive_chart_is_also_drawn_as_svg():
    """chart_data has the functions of charts.py with the same names."""
    for name in ("response_chart", "query_chart", "hour_chart", "heatmap", "month_chart"):
        assert callable(getattr(chart_data, name)) and callable(getattr(charts, name))
    assert "survival-pr" not in chart_data.INTERACTIVE, "only as SVG"


def test_the_response_bars_have_a_series_per_class():
    """The bars of the times until the first response, in the colours of the classes."""
    entries = [{"maintainer": 60.0}, {"bot": 5.0, "maintainer": 7200.0}, {}]
    drawn = chart_data.response_chart("Pull requests", entries, CLASSES, "dark")
    assert drawn["type"] == "bar" and drawn["labels"][0] == "1h"
    assert [d["label"] for d in drawn["datasets"]] == ["maintainer", "bot"]
    assert drawn["datasets"][1]["backgroundColor"] == "#9ccc9c"
    assert drawn["datasets"][0]["data"][:3] == [1, 1, 0], "within 1h, then within 3h"
    assert drawn["title"] == "Pull requests (3, 1 without a response)"
    assert drawn["ink"] == charts.INK["dark"] and not drawn["empty"]


def test_a_chart_without_data_is_empty():
    """Without responses the page keeps the SVG, which says so."""
    assert chart_data.response_chart("Issues", [{}], CLASSES)["empty"]
    assert chart_data.month_chart({})["empty"] and chart_data.month_chart({})["labels"] == []


def test_the_heat_map_has_a_cell_per_weekday_and_hour():
    """168 cells, the weekdays as rows and the colours from few to many."""
    grid = [[0] * 24 for _ in range(7)]
    grid[1][8] = 3
    drawn = chart_data.heatmap(grid)
    cells = drawn["datasets"][0]["data"]
    assert drawn["type"] == "matrix" and len(cells) == 168
    assert {"x": "08:00", "y": "Tue", "v": 3} in cells
    assert drawn["rows"][0] == "Mon" and drawn["heat"] == charts.HEAT_STOPS


def test_the_months_are_stacked_without_gaps():
    """Every month from the first to the last, each kind a series."""
    drawn = chart_data.month_chart({(2025, 12): {"commit": 2}, (2026, 2): {"issue": 1}})
    assert drawn["labels"] == ["2025-12", "2026-01", "2026-02"] and drawn["stacked"]
    commits = next(d for d in drawn["datasets"] if d["label"] == "commit")
    assert commits["data"] == [2, 0, 0]


def test_the_response_months_are_hours_with_their_counts():
    """The median in hours per month, a month without responses has no point."""
    drawn = chart_data.response_month_chart({(2026, 1): [3600.0, 7200.0], (2026, 3): [60.0]})
    series = drawn["datasets"][0]
    assert series["data"] == [1.5, None, pytest.approx(1 / 60)]
    assert series["counts"] == [2, 0, 1] and drawn["durations"] == "y"


@pytest.mark.django_db
def test_the_pages_draw_their_charts_with_chart_js(world, signed_in):
    """The charts link to their data; the pages load Chart.js; the data is JSON."""
    pk = world["project"].pk
    page = signed_in.get(f"/s/{pk}/people/bob/").content.decode()
    assert f'data-chart-json="/s/{pk}/chart/heatmap.json?login=bob' in page
    assert "vendor/chartjs/chart.umd.js" in page and "js/charts.js" in page
    overview = signed_in.get(f"/s/{pk}/").content.decode()
    assert f'data-chart-json="/s/{pk}/chart/responses-pr.json' in overview
    assert f'data-chart-json="/s/{pk}/chart/survival-pr.json' not in overview
    answer = signed_in.get(f"/s/{pk}/chart/hours.json?login=bob&theme=dark")
    assert answer.status_code == 200 and answer.json()["ink"] == charts.INK["dark"]
    assert signed_in.get(f"/s/{pk}/chart/survival-pr.json").status_code == 404
    assert signed_in.get(f"/s/{pk}/chart/query.json?where=prs_total+>+0").json()["type"] == "bar"


def test_a_heat_map_without_activity_is_empty():
    """Cells of 0 are no data: the page keeps the SVG, which says so."""
    assert chart_data.heatmap([[0] * 24 for _ in range(7)])["empty"]
    grid = [[0] * 24 for _ in range(7)]
    grid[6][23] = 1
    assert not chart_data.heatmap(grid)["empty"]


def test_lines_without_points_and_bars_of_zero_are_empty():
    """Months without responses (None) and bars of 0 count as no data."""
    assert chart_data.response_month_chart({})["empty"]
    assert chart_data.hour_chart([[0] * 24 for _ in range(7)])["empty"]
    assert chart_data.query_chart([], [], "activity_total")["empty"]
    assert not chart_data.query_chart(["bob"], [0.5], "activity_total")["empty"]


@pytest.mark.django_db
def test_unknown_charts_and_themes(world, signed_in):
    """A chart that does not exist is not found; an unknown theme is light."""
    pk = world["project"].pk
    assert signed_in.get(f"/s/{pk}/chart/nothing.json").status_code == 404
    assert signed_in.get(f"/s/{pk}/chart/nothing.svg").status_code == 404
    light = signed_in.get(f"/s/{pk}/chart/hours.json?theme=purple").json()
    assert light["ink"] == charts.INK["light"]
    assert signed_in.get("/s/999999/chart/hours.json").status_code == 404
