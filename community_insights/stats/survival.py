"""Response times with the items that got no response yet.

Response times with the items that got no response yet (censored data): Kaplan-Meier with
scipy.stats.ecdf.
"""

import numpy
import scipy.stats

from .responses import Times


def survival(entries: list[Times], observed: list[float], name: str | None):
    """The Kaplan-Meier survival function of the time until a response.

    The survival function of the time until the first response of a class (None: of anybody), or
    None without any response. An item without such a response is censored at the time it was
    observed.
    """
    responded, waited = [], []
    for entry, seconds in zip(entries, observed, strict=True):
        found = entry.get(name) if name else (min(entry.values()) if entry else None)
        if found is None:
            waited.append(seconds)
        else:
            responded.append(found)
    if not responded:
        return None
    data = scipy.stats.CensoredData(uncensored=responded, right=waited)
    return scipy.stats.ecdf(data).sf


def quantile(sf, share: float) -> float | None:
    """The time by which a share of the items got a response.

    The time by which `share` of the items got a response: the first time the survival function
    is at or below 1 - share; None if it is never reached.
    """
    reached = numpy.nonzero(sf.probabilities <= 1 - share + 1e-12)[0]
    return float(sf.quantiles[reached[0]]) if len(reached) else None
