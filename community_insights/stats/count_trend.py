"""Whether counts per day, week or month go up or down: a statistical trend, with statsmodels."""

import math
import warnings
from dataclasses import dataclass

from ..heavy import LOCK

MIN_BARS = 4  # fewer days, weeks or months give no trend
MIN_TOTAL = 5  # nor do fewer than five contributions or contributors in all
MIN_FILLED = 2  # nor counts in only one bar: from nothing to something has no rate
SIGNIFICANCE = 0.05  # a p-value below it is a clear trend


@dataclass(frozen=True)
class CountTrend:
    """How a count changes from one day, week or month to the next.

    A quasi-Poisson regression (a generalized linear model of statsmodels with a logarithmic
    link): the count changes by the same factor from each bar to the next. The part of a bar
    inside the time range is its exposure, so a week that has just begun is not taken as a
    drop. The spread of the counts is estimated from the data (Pearson's chi-squared), so
    counts that vary more than by chance widen the confidence interval; counts that vary less
    keep that of chance (Poisson), so a few counts never give a narrow interval. The
    confidence interval and the p-value use Student's t distribution with n - 2 degrees of
    freedom, as the spread is estimated from as few as 4 bars.

    Attributes:
        size: ``day``, ``week``, ``month`` or ``year``: the length of a bar.
        bars: How many bars were fitted.
        percent: How much the count grows (positive) or shrinks (negative) from one bar to the
            next, in percent.
        low: The lower end of the 95 % confidence interval of ``percent``.
        high: The upper end of the 95 % confidence interval of ``percent``.
        p_value: The probability of a change like this, or a bigger one, if the count did not
            change at all.
        first: The count of the line at the first bar.
        last: The count of the line at the last bar.
    """

    size: str
    bars: int
    percent: float
    low: float
    high: float
    p_value: float
    first: float
    last: float

    @property
    def clear(self) -> bool:
        """Whether the trend is statistically significant: a p-value below 0.05.

        Examples:
            >>> CountTrend("week", 8, 5.0, 1.0, 9.0, 0.01, 3.0, 4.0).clear
            True
        """
        return self.p_value < SIGNIFICANCE

    @property
    def growing(self) -> bool:
        """Whether the count grows."""
        return self.percent > 0

    @property
    def amount(self) -> float:
        """How much it grows or shrinks per bar, in percent, without its sign."""
        return abs(self.percent)

    @property
    def margin(self) -> float:
        """Half the width of the confidence interval, in percentage points: the error margin.

        Examples:
            >>> CountTrend("week", 8, 5.0, 1.0, 9.0, 0.01, 3.0, 4.0).margin
            4.0
        """
        return (self.high - self.low) / 2

    @property
    def total(self) -> float:
        """How much the line changes from the first bar to the last, in percent.

        Examples:
            >>> round(CountTrend("week", 3, 100.0, 50.0, 150.0, 0.01, 1.0, 4.0).total)
            300
        """
        return (self.last / self.first - 1) * 100 if self.first else 0.0


def percent(log_change: float) -> float:
    """A change in percent from a change of the logarithm.

    Args:
        log_change: The slope of the logarithm of the count, per bar.

    Returns:
        The percent.

    Examples:
        >>> percent(0.0), round(percent(math.log(2)), 1)
        (0.0, 100.0)
    """
    return (math.exp(log_change) - 1) * 100


def count_trend(counts: list[int], exposure: list[float], size: str) -> CountTrend | None:
    """The trend of counts per day, week or month.

    Args:
        counts: The count of each bar, the first one first.
        exposure: The part of each bar inside the time range, from 0 to 1.
        size: ``day``, ``week``, ``month`` or ``year``.

    Returns:
        The trend; None with fewer than ``MIN_BARS`` bars, a total below ``MIN_TOTAL`` or
        counts in fewer than ``MIN_FILLED`` bars.
    """
    rows = [(i, c, e) for i, (c, e) in enumerate(zip(counts, exposure, strict=True)) if e > 0]
    if (
        len(rows) < MIN_BARS
        or sum(c for _, c, _ in rows) < MIN_TOTAL
        or sum(c > 0 for _, c, _ in rows) < MIN_FILLED
    ):
        return None
    with LOCK:  # see heavy.py
        import numpy
        import statsmodels.api as sm  # loaded when needed: it is large
        from statsmodels.tools.sm_exceptions import PerfectSeparationWarning

    bars = numpy.array([i for i, _, _ in rows], dtype=float)
    found = numpy.array([c for _, c, _ in rows], dtype=float)
    parts = numpy.array([e for _, _, e in rows], dtype=float)
    rates = found / parts
    if numpy.ptp(rates) == 0:  # the same every time: no change, and nothing to test
        rate = float(rates[0])
        return CountTrend(size, len(rows), 0.0, 0.0, 0.0, 1.0, rate, rate)
    model = sm.GLM(found, sm.add_constant(bars), family=sm.families.Poisson(), exposure=parts)
    with warnings.catch_warnings():  # counts that fit the line well are no error
        warnings.simplefilter("ignore", PerfectSeparationWarning)
        poisson = model.fit()
        spread = max(1.0, float(poisson.pearson_chi2) / max(1.0, float(poisson.df_resid)))
        fitted = model.fit(scale=spread, use_t=True)  # t with n - 2 degrees of freedom
    intercept, slope = (float(v) for v in fitted.params)
    low, high = (float(v) for v in fitted.conf_int(0.05)[1])
    p_value = float(fitted.pvalues[1])
    return CountTrend(
        size,
        len(rows),
        percent(slope),
        percent(low),
        percent(high),
        p_value,
        math.exp(intercept + slope * float(bars[0])),
        math.exp(intercept + slope * float(bars[-1])),
    )
