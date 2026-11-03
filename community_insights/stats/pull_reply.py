from dataclasses import dataclass
from datetime import datetime


@dataclass
class PullReply:
    """A pull request and whether its author answered the feedback on it.

    Attributes:
        author: The handle of the author.
        repository: The repository, ``owner/name``.
        number: The number of the pull request.
        title: Its title.
        state: ``open`` or ``closed``.
        merged: Whether it was merged; then it needs no answer.
        closed_by: Who closed it, "" if unknown or open.
        created_at: When it was opened.
        first_feedback: When somebody else first commented or reviewed, None without.
        answered: None without feedback; otherwise whether the author answered it.
    """

    author: str
    repository: str
    number: int
    title: str
    state: str
    merged: bool
    closed_by: str
    created_at: datetime
    first_feedback: datetime | None
    answered: bool | None

    @property
    def closed_by_author(self) -> bool:
        """Whether its author closed it without merging it: the author gave it up."""
        return (
            self.state == "closed"
            and not self.merged
            and self.closed_by.lower() == self.author.lower()
        )

    @property
    def counted(self) -> bool:
        """Whether it counts for the replies: not merged and not closed by its author.

        Examples:
            >>> from datetime import datetime
            >>> def pull(state="open", merged=False, closed_by=""):
            ...     return PullReply("kim", "o/r", 1, "", state, merged, closed_by,
            ...                      datetime(2026, 1, 1), None, None)
            >>> pull().counted, pull("closed", closed_by="maint").counted
            (True, True)
            >>> pull("closed", merged=True).counted, pull("closed", closed_by="Kim").counted
            (False, False)
        """
        return not self.merged and not self.closed_by_author

    @property
    def unanswered(self) -> bool:
        """Whether it waits for an answer of its author: counted, with feedback, no answer."""
        return self.answered is False and self.counted

    @property
    def closed_by_others(self) -> bool:
        """Whether somebody else than the author closed it without merging it."""
        return (
            self.state == "closed"
            and not self.merged
            and bool(self.closed_by)
            and self.closed_by.lower() != self.author.lower()
        )
