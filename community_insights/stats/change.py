"""A number of a time range next to the same number of the period before it."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Change:
    """A number of a time range and the same number of the period of the same length before.

    Attributes:
        now: The number in the time range.
        before: The number in the period before; None when there is nothing to compare with,
            such as for all time.

    Examples:
        >>> Change(15, 10).percent, Change(15, 10).difference
        (50.0, 5)
        >>> Change(3, 0).percent is None, Change(3, None).difference is None
        (True, True)
    """

    now: int
    before: int | None = None

    @property
    def difference(self) -> int | None:
        """How many more (positive) or fewer (negative) than before; None without before."""
        return None if self.before is None else self.now - self.before

    @property
    def percent(self) -> float | None:
        """The change in percent of before; None without before or when it was 0."""
        if not self.before:
            return None
        return (self.now - self.before) / self.before * 100
