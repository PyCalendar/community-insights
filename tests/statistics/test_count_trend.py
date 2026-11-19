"""The statistical trend of the contributions and contributors per day, week or month."""

from datetime import UTC, datetime

import pytest

from community_insights import stats
from community_insights.stats.periods import exposure, people_by

WEEKS = [1.0] * 8


def test_a_steady_growth_is_significant():
    """Counts that grow each week: a clear increase, with its confidence interval."""
    found = stats.count_trend([2, 3, 5, 4, 7, 8, 10, 12], WEEKS, "week")
    assert found.clear and found.growing
    assert 5 < found.low < found.percent < found.high < 50
    assert found.margin == pytest.approx((found.high - found.low) / 2)
    assert found.first < 3 < 12 < found.last + 1


def test_counts_that_stay_the_same_are_no_trend():
    """Counts that go up and down a little: not significant."""
    found = stats.count_trend([5, 4, 6, 5, 5, 4, 6, 5], WEEKS, "week")
    assert not found.clear and found.p_value > 0.5
    assert found.low < 0 < found.high, "the interval holds no change"


def test_exactly_the_same_count_every_week():
    """No change and nothing to test."""
    found = stats.count_trend([3, 3, 3, 3], [1.0] * 4, "week")
    assert (found.percent, found.p_value, found.first, found.last) == (0.0, 1.0, 3.0, 3.0)
    assert not found.clear


def test_a_shrinking_count():
    """Fewer each month: a decrease."""
    found = stats.count_trend([40, 30, 25, 20, 12, 10], [1.0] * 6, "month")
    assert found.clear and not found.growing and found.amount == -found.percent


def test_counts_that_scatter_widen_the_margin():
    """More spread than by chance (overdispersion) makes the interval wider."""
    calm = stats.count_trend([10, 11, 12, 13, 14, 15, 16, 17], WEEKS, "week")
    wild = stats.count_trend([2, 20, 4, 25, 6, 30, 3, 40], WEEKS, "week")
    assert wild.margin > 2 * calm.margin


def test_counts_that_fit_too_well_keep_the_margin_of_chance():
    """Doubling each week fits the line exactly: the interval stays that of Poisson."""
    found = stats.count_trend([1, 2, 4, 8], [1.0] * 4, "week")
    assert found.percent == pytest.approx(100)
    assert found.low < 50 and found.high > 150


def test_a_week_that_has_just_begun_is_no_drop():
    """The last week is a third over: its count is taken as a third of a week."""
    whole = stats.count_trend([6, 6, 6, 6], [1.0] * 4, "week")
    begun = stats.count_trend([6, 6, 6, 2], [1, 1, 1, 1 / 3], "week")
    assert whole.percent == begun.percent == 0.0


@pytest.mark.parametrize(
    "counts",
    [
        [1, 2, 3],  # too few bars
        [1, 0, 1, 1],  # too few in all
        [0, 0, 0, 9],  # all in one bar: no rate to fit
        [0, 0, 0, 0],
    ],
)
def test_too_little_data_gives_no_trend(counts):
    """A trend needs bars, counts and more than one bar with them."""
    assert stats.count_trend(counts, [1.0] * len(counts), "week") is None


def test_bars_outside_the_range_are_left_out():
    """A bar without any time in the range does not count."""
    assert stats.count_trend([5, 5, 5, 5], [1, 1, 1, 0], "week") is None


def test_the_part_of_each_bar_in_the_time_range():
    """A range from a Wednesday noon to the next Monday: parts of two weeks."""
    start = datetime(2026, 1, 7, 12, tzinfo=UTC)  # Wednesday
    found = exposure(start, datetime(2026, 1, 13, tzinfo=UTC), "week", UTC)
    assert found == pytest.approx([4.5 / 7, 1 / 7])


def test_people_per_bar_count_each_person_once():
    """Two contributions of Ann on one day are one contributor; outside the range nothing."""
    start, end = datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 3, tzinfo=UTC)
    at = datetime(2026, 1, 1, 9, tzinfo=UTC)
    events = [("Ann", at), ("ann", at), ("bo", at), ("cy", datetime(2026, 1, 5, tzinfo=UTC))]
    assert people_by(events, start, end, "day", UTC) == [2, 0]
