import math
from dataclasses import dataclass

import numpy
import scipy.stats

from .format import format_duration
from .responses import Times
from .survival import quantile, survival


@dataclass
class FitRow:
    """A row of the table of the response times: a class, a fit and its numbers as text."""

    name: str
    n: int
    fit: str
    average: str
    std_error: str
    median: str
    p95: str


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


    """

    def show(seconds) -> str:
        return format_duration(float(seconds))  # also numpy numbers

    rows = []
    for name in names:
        x = numpy.array([e[name] for e in entries if name in e], dtype=float)
        if not len(x):
            continue
        n = len(x)
        error = show(scipy.stats.sem(x)) if n > 1 else "-"
        rows.append(
            FitRow(
                name,
                n,
                "measured",
                show(x.mean()),
                error,
                show(numpy.median(x)),
                show(numpy.percentile(x, 95)),
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
