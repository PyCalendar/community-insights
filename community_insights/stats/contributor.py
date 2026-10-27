from dataclasses import dataclass, field
from datetime import datetime
from statistics import median


@dataclass
class Contributor:
    """What one person did in the repositories.

    Attributes:
        login: The handle.
        prs_opened: Pull requests opened.
        prs_merged: Of those, merged.
        prs_closed: Of those, closed without merging.
        prs_open: Of those, still open.
        issues_opened: Issues opened.
        issues_closed: Of those, closed.
        issues_open: Of those, still open.
        comments: Comments on items of others.
        reviews: Reviews of pull requests of others.
        commits: Commits.
        first: The time of the first activity.
        last: The time of the last activity.
        months: The (year, month) of each activity.
        delays: The seconds until their first response on each item of others.
        name: The name of the profile.
        location: The location of the profile.
        avatar_url: The address of the picture of the profile.
        klass: The name of the class of people.
        association: The most privileged status seen, lowercase.
        prs_commented: The ids of the pull requests of others commented on.
        prs_reviewed: The ids of the pull requests of others reviewed.
        issues_commented: The ids of the issues of others commented on.
        merges: Pull requests merged by the person.
        merge_days: For their merged pull requests: the days until merged.
    """

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
    association: str = ""  # the most privileged one seen, lowercase
    prs_commented: set = field(default_factory=set)  # pull requests of others commented on
    prs_reviewed: set = field(default_factory=set)  # pull requests of others reviewed
    issues_commented: set = field(default_factory=set)  # issues of others commented on
    merges: int = 0  # pull requests merged by the person
    merge_days: list[float] = field(default_factory=list)  # their pull requests, until merged

    @property
    def active_months(self) -> int:
        """Months with any activity."""
        return len(self.months)

    @property
    def median_response(self) -> float | None:
        """Median seconds until their first response on items of others."""
        return median(self.delays) if self.delays else None

    @property
    def days_to_merge(self) -> float | None:
        """Median days until their pull requests were merged; None without merged ones."""
        return round(median(self.merge_days), 1) if self.merge_days else None

    @property
    def activity(self) -> int:
        """Pull requests, issues, comments, reviews and commits together."""
        return self.prs_opened + self.issues_opened + self.comments + self.reviews + self.commits
