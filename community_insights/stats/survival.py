"""Response times with the items that got no response yet.

Response times with the items that got no response yet (censored data): Kaplan-Meier with
lifelines.
"""

import math
import warnings

from lifelines import KaplanMeierFitter
from lifelines.utils import qth_survival_time

from .responses import Times


def waits(entries: list[Times], observed: list[float], name: str | None):
    """The time of each item until a response of a class, and whether one came.

    Args:
        entries: The seconds until the first response of each class, one dictionary per item.
        observed: How long each item was observed.
        name: The class, None for the first response of anybody.

    Returns:
        The seconds of each item, and for each whether it got a response; an item without
        one counts with the time it was observed (censored).

    Examples:
        >>> waits([{"bot": 5.0}, {}], [10.0, 20.0], "bot")
        ([5.0, 20.0], [True, False])
    """
    durations, responded = [], []
    for entry, seconds in zip(entries, observed, strict=True):
        found = entry.get(name) if name else (min(entry.values()) if entry else None)
        durations.append(seconds if found is None else found)
        responded.append(found is not None)
    return durations, responded


def survival(entries: list[Times], observed: list[float], name: str | None):
    """The Kaplan-Meier estimate of the time until a response.

    The share of the items still without a response of a class (None: of anybody) over time,
    with its confidence interval; None without any response. An item without such a response
    is censored at the time it was observed.

    Args:
        entries: The seconds until the first response of each class, one dictionary per item.
        observed: How long each item was observed.
        name: The class, None for the first response of anybody.

    Returns:
        The fitted ``lifelines.KaplanMeierFitter``, or None.
    """
    durations, responded = waits(entries, observed, name)
    if not any(responded):
        return None
    with warnings.catch_warnings():  # lifelines warns about times of 0
        warnings.simplefilter("ignore")
        return KaplanMeierFitter(label=name or "").fit(durations, responded)


def quantile(fitted, share: float) -> float | None:
    """The time by which a share of the items got a response.

    The time by which `share` of the items got a response: the first time the share without
    a response is at or below 1 - share; None if it is never reached.

    Args:
        fitted: The estimate of ``survival``.
        share: The share, 0 to 1.

    Returns:
        The seconds, or None.

    Examples:
        >>> fitted = survival([{"a": 10.0}, {"a": 20.0}, {}], [10.0, 20.0, 30.0], "a")
        >>> quantile(fitted, 0.5), quantile(fitted, 0.95)
        (20.0, None)
    """
    found = float(qth_survival_time(1 - share, fitted.survival_function_))
    return None if math.isinf(found) else found
