"""Several GitHub tokens used one after the other, each within its limit."""

from ..errors import AllTokensUsedUp, FetchLimitReached
from .access import ask, ask_one, entries_for, points_left, pool_for
from .allowance import HourAllowance
from .entry import HOUR, Entry
from .pool import TokenPool

# names used in this package
LimitReached = FetchLimitReached
NoTokenLeft = AllTokensUsedUp

__all__ = [
    "HOUR",
    "Entry",
    "HourAllowance",
    "LimitReached",
    "NoTokenLeft",
    "TokenPool",
    "ask",
    "ask_one",
    "entries_for",
    "points_left",
    "pool_for",
]
