from dataclasses import dataclass, field
from datetime import datetime
from statistics import median


@dataclass
class Contributor:
    """What one person did in the repositories."""

    login: str
    prs_opened: int = 0
    prs_merged: int = 0
    prs_closed: int = 0
    prs_open: int = 0
    issues_opened: int = 0
    issues_closed: int = 0
    issues_open: int = 0
    comments: int = 0
    reviews: int = 0
    commits: int = 0
    first: datetime | None = None
    last: datetime | None = None
    months: set = field(default_factory=set)
    delays: list[float] = field(default_factory=list)
    name: str = ""
    location: str = ""
    avatar_url: str = ""
    klass: str = ""

    @property
    def active_months(self) -> int:
        """Months with any activity."""
        return len(self.months)

    @property
    def median_response(self) -> float | None:
        """Median seconds until their first response on items of others."""
        return median(self.delays) if self.delays else None

    @property
    def activity(self) -> int:
        """Pull requests, issues, comments, reviews and commits together."""
        return self.prs_opened + self.issues_opened + self.comments + self.reviews + self.commits
