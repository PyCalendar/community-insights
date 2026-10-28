"""Whether the first responses get faster or slower: statsmodels."""

from datetime import UTC, datetime, timedelta

import pytest

from community_insights import stats
from community_insights.stats.trend import MIN_RESPONSES

START = datetime(2026, 1, 1, tzinfo=UTC)


def rows(factor_per_month, count=40, spread=0.0):
    """Items, one every 3 days, whose response time changes by a factor per month."""
    found = []
    for index in range(count):
        days = 3 * index
        seconds = 3600 * factor_per_month ** (days / 30.44) * (1 + spread * (-1) ** index)
        found.append((START + timedelta(days=days), {"maintainer": seconds}, seconds))
    return found


def test_responses_that_get_faster():
    """Halving each month is 50 % faster, a clear trend."""
    trend = stats.trend(rows(0.5))
    assert trend is not None and trend.clear and trend.faster
    assert trend.percent_per_month == pytest.approx(-50, abs=0.5)
    assert trend.bounds[0] <= trend.size <= trend.bounds[1]
    assert trend.responses == 40


def test_responses_that_get_slower():
    """Doubling each month is 100 % slower."""
    trend = stats.trend(rows(2.0, spread=0.1))
    assert trend is not None and trend.clear and not trend.faster
    assert trend.percent_per_month == pytest.approx(100, rel=0.05)


def test_no_trend():
    """Times that only jump around show no clear trend."""
    trend = stats.trend(rows(1.0, spread=0.5))
    assert trend is not None and not trend.clear


def test_too_few_responses_give_no_trend():
    """Below MIN_RESPONSES, and items without a response do not count."""
    few = rows(0.5, count=MIN_RESPONSES - 1)
    assert stats.trend(few) is None
    unanswered = [(START, {}, 100.0)] * 50
    assert stats.trend(few + unanswered) is None


def test_all_on_one_day_give_no_trend():
    """Without time between the items there is no line."""
    same_day = [(START, {"bot": float(s)}, 1.0) for s in range(20)]
    assert stats.trend(same_day) is None


def test_the_first_response_of_anybody_counts():
    """The fastest class of an item is its first response."""
    found = [(created, {**times, "bot": 1.0}, seconds) for created, times, seconds in rows(2.0)]
    trend = stats.trend(found)
    assert trend is not None and not trend.clear, "the bot answers at once, always"
    assert trend.percent_per_month == 0


@pytest.mark.django_db
def test_the_overview_shows_the_trend_and_the_curves(world, signed_in):
    """The overview says the trend of each kind and shows the Kaplan-Meier curves."""
    pk = world["project"].pk
    page = signed_in.get(f"/s/{pk}/").content.decode()
    assert 'data-trend="pr"' in page and 'data-trend="issue"' in page
    assert "too few responses to tell" in page
    assert f"/s/{pk}/chart/survival-pr.svg" in page
    assert "response-times.html#kaplan-meier-curve" in page
    assert "response-times.html#trend" in page
    chart = signed_in.get(f"/s/{pk}/chart/survival-pr.svg")
    assert chart.status_code == 200 and chart["Content-Type"] == "image/svg+xml"
    assert signed_in.get(f"/s/{pk}/share/survival-issue/").status_code == 200


def test_exactly_the_least_number_of_responses_gives_a_trend():
    """MIN_RESPONSES responses are enough."""
    assert stats.trend(rows(0.5, count=MIN_RESPONSES)) is not None


def test_responses_after_zero_seconds_are_counted():
    """log1p counts a response after 0 seconds without an error."""
    found = [(START + timedelta(days=i), {"bot": 0.0 if i % 2 else 60.0}, 1.0) for i in range(20)]
    trend = stats.trend(found)
    assert trend is not None and 0 <= trend.p_value <= 1


def test_the_order_of_the_items_does_not_matter():
    """The trend is the same for items in any order."""
    found = rows(0.5, spread=0.2)
    forward, backward = stats.trend(found), stats.trend(found[::-1])
    assert forward is not None and backward is not None
    assert forward.percent_per_month == pytest.approx(backward.percent_per_month)
    assert forward.p_value == pytest.approx(backward.p_value)


def test_bounds_without_signs_are_sorted():
    """The confidence interval of a slowing trend, from the smaller end."""
    from community_insights.stats import Trend

    assert Trend(20, 30.0, 10.0, 50.0, 0.01).bounds == (10.0, 50.0)
    assert Trend(20, 30.0, 10.0, 50.0, 0.05).clear is False


def test_the_code_of_the_documentation_gives_the_same_trend():
    """docs/how-to/verify.rst computes the trend from the downloaded responses."""
    import numpy
    import pandas
    import statsmodels.api as sm

    found = rows(0.5, spread=0.3)
    table = pandas.DataFrame(
        {
            "created_at": [created.isoformat().replace("+00:00", "Z") for created, _, _ in found],
            "seconds_any": [min(times.values()) for _, times, _ in found],
        }
    )
    # the code of the documentation
    answered = table.dropna(subset=["seconds_any"])
    days = (
        pandas.to_datetime(answered["created_at"])
        - pandas.to_datetime(answered["created_at"]).min()
    ).dt.total_seconds() / 86400
    fitted = sm.OLS(numpy.log1p(answered["seconds_any"]), sm.add_constant(days)).fit()
    percent = (numpy.exp(fitted.params.iloc[1] * 30.44) - 1) * 100
    trend = stats.trend(found)
    assert trend is not None
    assert percent == pytest.approx(trend.percent_per_month)
    assert fitted.pvalues.iloc[1] == pytest.approx(trend.p_value)
