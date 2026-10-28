"""Whether the responses get faster or slower over time, with statsmodels."""

import math
from dataclasses import dataclass
from datetime import datetime

import numpy
import statsmodels.api as sm

from .responses import Times

MIN_RESPONSES = 10  # fewer give no trend
DAYS_PER_MONTH = 30.44


@dataclass(frozen=True)
class Trend:
    """How the time until the first response changes per month.

    A line through the logarithm of the seconds until the first response of anybody, over the
    day the item was created (ordinary least squares of statsmodels): the times change by the
    same factor each month.

    Attributes:
        responses: How many items with a response were counted.
        percent_per_month: How much longer (positive) or shorter (negative) the time until the
            first response gets per month, in percent.
        low: The lower end of the 95 % confidence interval of ``percent_per_month``.
        high: The upper end of the 95 % confidence interval of ``percent_per_month``.
        p_value: The probability of such a change, or a bigger one, if there were no trend.
    """

    responses: int
    percent_per_month: float
    low: float
    high: float
    p_value: float

    @property
    def clear(self) -> bool:
        """Whether the trend is clear: a p-value below 0.05."""
        return self.p_value < 0.05

    @property
    def faster(self) -> bool:
        """Whether the responses get faster."""
        return self.percent_per_month < 0

    @property
    def size(self) -> float:
        """How much faster or slower, in percent per month, without its sign."""
        return abs(self.percent_per_month)

    @property
    def bounds(self) -> tuple[float, float]:
        """The confidence interval of ``size``: the smaller and the bigger end, without signs.

        Examples:
            >>> Trend(20, -10.0, -15.0, -4.0, 0.01).bounds
            (4.0, 15.0)
        """
        ends = abs(self.low), abs(self.high)
        return min(ends), max(ends)


def percent(log_change_per_day: float) -> float:
    """The change of a month, in percent, of a change of the logarithm per day.

    Args:
        log_change_per_day: The slope of the line through the logarithms, per day.

    Returns:
        The percent.

    Examples:
        >>> round(percent(0.0), 1), round(percent(math.log(2) / DAYS_PER_MONTH), 1)
        (0.0, 100.0)
    """
    return (math.exp(log_change_per_day * DAYS_PER_MONTH) - 1) * 100


def trend(rows: list[tuple[datetime, Times, float]]) -> Trend | None:
    """The trend of the time until the first response of anybody.

    Args:
        rows: For each item the time it was created, the seconds until the first response of
            each class, and how long it was observed (``stats.response_rows``).

    Returns:
        The trend; None with fewer than ``MIN_RESPONSES`` responses, or all on one day.
    """
    answered = [(created, min(times.values())) for created, times, _ in rows if times]
    if len(answered) < MIN_RESPONSES:
        return None
    start = min(created for created, _ in answered)
    days = numpy.array([(created - start).total_seconds() / 86400 for created, _ in answered])
    if numpy.ptp(days) == 0:
        return None
    seconds = numpy.log1p(numpy.array([value for _, value in answered]))
    if numpy.ptp(seconds) == 0:  # always the same time: no change, and no line to test
        return Trend(len(answered), 0.0, 0.0, 0.0, 1.0)
    fitted = sm.OLS(seconds, sm.add_constant(days)).fit()
    low, high = fitted.conf_int(0.05)[1]
    return Trend(
        len(answered),
        percent(float(fitted.params[1])),
        percent(float(low)),
        percent(float(high)),
        float(fitted.pvalues[1]),
    )
