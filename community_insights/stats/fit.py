import math
from dataclasses import dataclass

import numpy
import scipy.stats

from .format import format_duration
from .responses import Times
from .survival import quantile, survival


@dataclass
class FitRow:
    """A row of the table of the response times: a class, a fit and its numbers as text.

    Attributes:
        name: The class of people.
        n: How many items are counted.
        fit: ``measured``, ``normal``, ``exponential`` or ``Kaplan-Meier``.
        average: The average, as text.
        std_error: The standard error of the average, as text.
        median: The median, as text.
        p95: The 95th percentile, as text.
        error_seconds: The standard error in seconds, None without one.
    """

    name: str
    n: int
    fit: str
    average: str
    std_error: str
    median: str
    p95: str
    error_seconds: float | None = None  # the standard error as a number, None without one


def summary(
    entries: list[Times], names: list[str], observed: list[float] | None = None
) -> list[FitRow]:
    """Measured and fitted response times of each class.

    Per class three rows: measured, normal and exponential, computed with scipy so the numbers
    can be checked with the downloaded table (see docs/how-to/verify.rst), x being the seconds
    of a class:

    - measured: mean, standard error `scipy.stats.sem(x)`, median and the 95th
    percentile `numpy.percentile(x, 95)`
    - normal: `mu, sigma = scipy.stats.norm.fit(x)` (maximum likelihood), the
    standard error sigma / sqrt(n), the median mu, the 95th percentile
    `norm.ppf(0.95, mu, sigma)`
    - exponential: `loc, scale = scipy.stats.expon.fit(x, floc=0)`; the mean is
    scale, its standard error scale / sqrt(n), `expon.median(scale=scale)`
    and `expon.ppf(0.95, scale=scale)`
    - Kaplan-Meier (with `observed`): the items without a response of the class
    count as waiting at least as long as they were observed (until closed or
    now); median and 95th percentile of `scipy.stats.ecdf` of
    `scipy.stats.CensoredData`, "-" if not reached. The count is of all items.


    Args:
        entries: The seconds until the first response of each class, one dictionary per item.
        names: The classes, in their order.
        observed: How long each item was observed, for Kaplan-Meier; None leaves it out.

    Returns:
        The rows.
    """

    def show(seconds) -> str:
        return format_duration(float(seconds))  # also numpy numbers

    rows = []
    for name in names:
        x = numpy.array([e[name] for e in entries if name in e], dtype=float)
        if not len(x):
            continue
        n = len(x)
        sem = float(scipy.stats.sem(x)) if n > 1 else None
        error = show(sem) if sem is not None else "-"
        rows.append(
            FitRow(
                name,
                n,
                "measured",
                show(x.mean()),
                error,
                show(numpy.median(x)),
                show(numpy.percentile(x, 95)),
                sem,
            )
        )
        mu, sigma = scipy.stats.norm.fit(x)
        rows.append(
            FitRow(
                name,
                n,
                "normal",
                show(mu),
                show(sigma / math.sqrt(n)) if n > 1 else "-",
                show(mu),
                show(scipy.stats.norm.ppf(0.95, mu, sigma)) if n > 1 else "-",
                float(sigma / math.sqrt(n)) if n > 1 else None,
            )
        )
        _, scale = scipy.stats.expon.fit(x, floc=0)
        rows.append(
            FitRow(
                name,
                n,
                "exponential",
                show(scale),
                show(scale / math.sqrt(n)),
                show(scipy.stats.expon.median(scale=scale)),
                show(scipy.stats.expon.ppf(0.95, scale=scale)),
                float(scale / math.sqrt(n)),
            )
        )
        if observed is not None:
            sf = survival(entries, observed, name)
            median, p95 = quantile(sf, 0.5), quantile(sf, 0.95)
            rows.append(
                FitRow(
                    name,
                    len(entries),
                    "Kaplan-Meier",
                    "-",
                    "-",
                    show(median) if median is not None else "-",
                    show(p95) if p95 is not None else "-",
                )
            )
    return rows


def best_fit(rows: list[FitRow]) -> str:
    """The fit with the lowest standard error, summed over the classes that have one.

    Args:
        rows: The rows of `summary`.

    Returns:
        The name of the fit, "measured" when no fit has a standard error.

    Examples:
        >>> rows = [FitRow("bot", 3, "measured", "", "", "", "", 40.0),
        ...         FitRow("bot", 3, "normal", "", "", "", "", 30.0),
        ...         FitRow("bot", 3, "Kaplan-Meier", "", "", "", "")]
        >>> best_fit(rows)
        'normal'
        >>> best_fit([])
        'measured'
    """
    errors: dict[str, float] = {}
    for row in rows:
        if row.error_seconds is not None:
            errors[row.fit] = errors.get(row.fit, 0.0) + row.error_seconds
    return min(errors, key=lambda fit: errors[fit]) if errors else "measured"
