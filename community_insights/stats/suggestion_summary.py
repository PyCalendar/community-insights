"""How many suggestions were applied, are open or unknown, and the colour of their badge."""

from dataclasses import dataclass

GREEN, YELLOW, RED, GREY = "green", "yellow", "red", "grey"
PULL_LABEL = "suggestions"  # the left side of the badge of a pull request


def pull_label(number: int, with_number: bool = False) -> str:
    """The left side of the badge of a pull request.

    Args:
        number: The number of the pull request.
        with_number: Whether it starts with ``PR #12`` (the parameter ``number=1``).

    Returns:
        The label.

    Examples:
        >>> pull_label(12), pull_label(12, with_number=True)
        ('suggestions', 'PR #12 suggestions')
    """
    return f"PR #{number} {PULL_LABEL}" if with_number else PULL_LABEL


@dataclass(frozen=True)
class SuggestionSummary:
    """The suggestions of a pull request or of the pull requests of a person.

    Attributes:
        applied: Applied ones.
        open: Ones not applied yet.
        unknown: Ones whose thread was resolved by somebody else or answered with another
            suggestion.
    """

    applied: int = 0
    open: int = 0
    unknown: int = 0

    @property
    def total(self) -> int:
        """All suggestions."""
        return self.applied + self.open + self.unknown

    @property
    def status(self) -> str:
        """The colour of the badge.

        Green if all were applied, red if one is open, yellow if some are unknown and none
        is open, grey without suggestions.

        Examples:
            >>> counts = ((2, 0, 0), (2, 1, 1), (2, 0, 1), (0, 0, 0))
            >>> [SuggestionSummary(*n).status for n in counts]
            ['green', 'red', 'yellow', 'grey']
        """
        if not self.total:
            return GREY
        if self.open:
            return RED
        if self.unknown:
            return YELLOW
        return GREEN

    @property
    def message(self) -> str:
        """The text of the badge, in English as the badges in READMEs.

        Examples:
            >>> SuggestionSummary(3, 1, 1).message, SuggestionSummary().message
            ('3/5 suggestions applied', 'no suggestions')
        """
        if not self.total:
            return "no suggestions"
        return f"{self.applied}/{self.total} suggestions applied"

    @property
    def fraction(self) -> str:
        """The short text of the badge of a pull request: applied of all.

        Examples:
            >>> SuggestionSummary(3, 1, 1).fraction, SuggestionSummary().fraction
            ('3/5', 'none')
        """
        if not self.total:
            return "none"
        return f"{self.applied}/{self.total}"

    @classmethod
    def of(cls, statuses) -> "SuggestionSummary":
        """The summary of statuses.

        Args:
            statuses: ``applied``, ``open`` or ``unknown`` for each suggestion.

        Returns:
            The summary.

        Examples:
            >>> SuggestionSummary.of(["applied", "open", "applied"])
            SuggestionSummary(applied=2, open=1, unknown=0)
        """
        found = list(statuses)
        return cls(found.count("applied"), found.count("open"), found.count("unknown"))
