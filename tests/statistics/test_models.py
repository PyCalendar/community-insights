"""A percentile of the response times with each statistical model."""

import pytest
import scipy.stats

from community_insights import stats

ENTRIES = [{"bot": 60.0, "maint": 600.0}, {"bot": 120.0}, {"maint": 3600.0}, {}]
OBSERVED = [7200.0, 7200.0, 7200.0, 10.0]


def test_measured_is_the_percentile_of_the_times():
    """Measured is the percentile of the times."""
    assert stats.model_percentile(ENTRIES, OBSERVED, "bot", 50, "measured") == (90.0, 2)
    assert stats.model_percentile(ENTRIES, OBSERVED, None, 50, "measured") == (120.0, 3)


def test_normal_and_exponential_are_the_quantiles_of_the_fits():
    """Normal and exponential are the quantiles of the fits."""
    x = [60.0, 120.0]
    mu, sigma = scipy.stats.norm.fit(x)
    normal, n = stats.model_percentile(ENTRIES, OBSERVED, "bot", 95, "normal")
    assert normal == pytest.approx(scipy.stats.norm.ppf(0.95, mu, sigma)) and n == 2
    exponential, _ = stats.model_percentile(ENTRIES, OBSERVED, "bot", 95, "exponential")
    assert exponential == pytest.approx(scipy.stats.expon.ppf(0.95, scale=90.0))


def test_normal_is_never_below_zero_and_needs_two_times():
    """Normal is never below zero and needs two times."""
    low, _ = stats.model_percentile(ENTRIES, OBSERVED, "maint", 1, "normal")
    assert low == 0.0
    assert stats.model_percentile([{"c": 60.0}], [60.0], "c", 50, "normal") == (None, 1)
    assert stats.model_percentile([{}], [60.0], "c", 50, "exponential") == (None, 0)


def test_a_percentile_of_100_of_a_fit_is_none():
    """A percentile of 100 of a fit is none."""
    assert stats.model_percentile(ENTRIES, OBSERVED, "bot", 100, "exponential")[0] is None


def test_kaplan_meier_counts_all_items():
    """Kaplan meier counts all items."""
    seconds, n = stats.model_percentile(ENTRIES, OBSERVED, "maint", 50, "kaplan-meier")
    assert n == 4
    assert seconds == 3600.0, "two of four answered by then; the fourth was watched too briefly"
    assert stats.model_percentile(ENTRIES, OBSERVED, "maint", 95, "kaplan-meier")[0] is None
    assert stats.model_percentile([{}], [5.0], "maint", 50, "kaplan-meier") == (None, 1)


def test_unknown_models():
    """Unknown models."""
    with pytest.raises(ValueError, match="no model"):
        stats.model_percentile(ENTRIES, OBSERVED, "bot", 50, "guess")
