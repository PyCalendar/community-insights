"""A percentile of the response times with one of the statistical models of the overview."""

import math

import numpy
import scipy.stats

from .responses import Times, percentile
from .survival import quantile, survival

# the models: their names in addresses, as on the overview
MODELS = ("measured", "normal", "exponential", "kaplan-meier")


def times_of(entries: list[Times], name: str | None) -> list[float]:
    """The seconds until the first response of a class, or of anybody.

    Args:
        entries: The seconds until the first response of each class, one dictionary per item.
        name: The class, None for the first response of anybody.

    Returns:
        The seconds of the items with such a response.
    """
    if name is None:
        return [min(e.values()) for e in entries if e]
    return [e[name] for e in entries if name in e]


def model_percentile(
    entries: list[Times], observed: list[float], name: str | None, p: float, model: str
) -> tuple[float | None, int]:
    """The time within which p percent of the first responses came, with a model.

    ``measured`` is the percentile of the times; ``normal`` and ``exponential`` the quantile
    of the fitted distribution, as in ``stats.summary``; ``kaplan-meier`` the time by which
    p percent of all items got a response, counting those without one as waiting.

    Args:
        entries: The seconds until the first response of each class, one dictionary per item.
        observed: How long each item was observed, for ``kaplan-meier``.
        name: The class, None for the first response of anybody.
        p: The percentile, 0 to 100.
        model: One of ``MODELS``.

    Returns:
        The seconds, None if the model gives none (too few responses, or a share that is
        never reached), and how many items were counted.

    Raises:
        ValueError: If the model is not one of ``MODELS``.

    Examples:
        >>> entries = [{"bot": 60.0}, {"bot": 120.0}, {}]
        >>> model_percentile(entries, [60.0, 120.0, 30.0], "bot", 50, "measured")
        (90.0, 2)
        >>> model_percentile(entries, [60.0, 120.0, 3600.0], "bot", 50, "kaplan-meier")
        (120.0, 3)
    """
    if model not in MODELS:
        raise ValueError(f"no model {model!r}")
    if model == "kaplan-meier":
        sf = survival(entries, observed, name)
        return (quantile(sf, p / 100) if sf is not None else None), len(entries)
    x = times_of(entries, name)
    if model == "measured":
        return percentile(x, p), len(x)
    if len(x) < 2 and model == "normal":
        return None, len(x)
    if not x:
        return None, 0
    if model == "normal":
        mu, sigma = scipy.stats.norm.fit(x)
        value = float(scipy.stats.norm.ppf(p / 100, mu, sigma))
    else:
        value = float(scipy.stats.expon.ppf(p / 100, scale=numpy.mean(x)))
    return (max(value, 0.0) if math.isfinite(value) else None), len(x)
