from dataclasses import dataclass, field

GREEN, YELLOW, RED = "green", "yellow", "red"


@dataclass
class ContributorReplies:
    """Whether a person answered the feedback on their pull requests.

    Feedback is a comment or review by somebody else than the author, and not by a bot. A
    pull request is answered when its author commented, reviewed or committed after the first
    feedback.

    Attributes:
        login: The handle of the author.
        prs: The pull requests the person opened that were not merged.
        with_feedback: Of those, the ones with feedback.
        unanswered: The numbers of the pull requests with feedback and no answer, by
            repository (``owner/name``).
        closed_by_others: Pull requests of the person that somebody else closed without
            merging them.
        closed: The pull requests of ``unanswered`` that are closed, as (repository, number).
        merged: The pull requests of the person that were merged; they need no answer.
        total: All pull requests of the person, also the merged ones and those the person
            closed.
    """

    login: str
    prs: int = 0
    with_feedback: int = 0
    unanswered: dict[str, list[int]] = field(default_factory=dict)
    closed_by_others: int = 0
    closed: set[tuple[str, int]] = field(default_factory=set)
    merged: int = 0
    total: int = 0

    def unanswered_in(self, closed: bool) -> dict[str, list[int]]:
        """The pull requests without an answer that are closed, or open.

        Args:
            closed: True for the closed ones, False for the open ones.

        Returns:
            Their numbers by repository, without the repositories that have none.

        Examples:
            >>> person = ContributorReplies("kim", unanswered={"o/r": [1, 2]}, closed={("o/r", 2)})
            >>> person.unanswered_in(closed=False), person.unanswered_in(closed=True)
            ({'o/r': [1]}, {'o/r': [2]})
        """
        found = {
            repository: [n for n in numbers if ((repository, n) in self.closed) == closed]
            for repository, numbers in self.unanswered.items()
        }
        return {repository: numbers for repository, numbers in found.items() if numbers}

    @property
    def unanswered_open(self) -> dict[str, list[int]]:
        """The open pull requests without an answer, by repository."""
        return self.unanswered_in(closed=False)

    @property
    def unanswered_closed(self) -> dict[str, list[int]]:
        """The closed pull requests without an answer, by repository."""
        return self.unanswered_in(closed=True)

    @property
    def unanswered_count(self) -> int:
        """The pull requests with feedback that the person did not answer."""
        return sum(len(numbers) for numbers in self.unanswered.values())

    @property
    def answered(self) -> int:
        """The pull requests with feedback that the person answered."""
        return self.with_feedback - self.unanswered_count

    @property
    def status(self) -> str:
        """The colour of the badge.

        Green if every feedback was answered; yellow if the person has only one pull request
        that was not merged and did not answer its feedback; red if some feedback was not
        answered.

        Examples:
            >>> ContributorReplies("kim", prs=2, with_feedback=2).status
            'green'
            >>> ContributorReplies("kim", prs=1, with_feedback=1, unanswered={"o/r": [3]}).status
            'yellow'
            >>> ContributorReplies("kim", prs=2, with_feedback=1, unanswered={"o/r": [3]}).status
            'red'
        """
        if not self.unanswered_count:
            return GREEN
        return YELLOW if self.prs == 1 else RED
