"""How many suggestions were applied, are open or unknown, and the colour of their badge."""

from dataclasses import dataclass

GREEN, YELLOW, RED, GREY = "green", "yellow", "red", "grey"


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
