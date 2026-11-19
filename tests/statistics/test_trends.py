"""The numbers of the page Trends: opened, closed, contributions and new contributors."""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from community_insights import stats
from community_insights.models import Event, Item, Repository
from community_insights.stats import periods
from community_insights.stats.change import Change
from community_insights.sync import store_repository

from ..fakes import repo

pytestmark = pytest.mark.django_db

SINCE = datetime(2026, 1, 8, tzinfo=UTC)  # the time range: one week
UNTIL = datetime(2026, 1, 15, tzinfo=UTC)
NOW = datetime(2026, 2, 1, tzinfo=UTC)


def day(number: int, hour: int = 12) -> datetime:
    """A time in January 2026.

    Args:
        number: The day of the month.
        hour: The hour, in UTC.

    Returns:
        The time.
    """
    return datetime(2026, 1, number, hour, tzinfo=UTC)


def opened(repository, kind, number, author, created, closed=None, merged=False, bot=False):
    """An item with the event of its opening.

    Args:
        repository: The repository.
        kind: ``pr`` or ``issue``.
        number: Its number.
        author: Who opened it.
        created: When.
        closed: When it was closed, None if open.
        merged: Whether it was merged.
        bot: Whether the author is a bot.

    Returns:
        The item.
    """
    item = Item.objects.create(
        repository=repository,
        kind=kind,
        number=number,
        author=author,
        author_is_bot=bot,
        state="closed" if closed else "open",
        merged=merged,
        created_at=created,
        updated_at=closed or created,
        closed_at=closed,
    )
    Event.objects.create(item=item, actor=author, kind=Event.OPENED, at=created, is_bot=bot)
    return item


def said(item, actor, at, kind=Event.COMMENT, bot=False):
    """A comment or review on an item.

    Args:
        item: The item.
        actor: Who.
        at: When.
        kind: ``comment`` or ``review``.
        bot: Whether it is a bot.
    """
    Event.objects.create(item=item, actor=actor, kind=kind, at=at, is_bot=bot)


@pytest.fixture
def week():
    """Issues and pull requests in the week of the time range and in the week before.

    Issues: ann opens #1 in the week before; bob opens #2 in the week, Ann (another case)
    comments on it, a bot too; cid opens #3 in the week, closed in the week; #4 was opened
    before the week and closed in it.
    Pull requests: bob opens #10 in the week before; dot opens #11 in the week, merged in
    it, bob reviews it; dot opens #12, closed unmerged after the week; a bot opens #13.
    """
    repository = store_repository(repo("o/r", 1))
    opened(repository, Item.ISSUE, 1, "ann", day(2))
    issue = opened(repository, Item.ISSUE, 2, "bob", day(9))
    said(issue, "Ann", day(10))
    said(issue, "ci[bot]", day(10), bot=True)
    opened(repository, Item.ISSUE, 3, "cid", day(11), closed=day(12))
    opened(repository, Item.ISSUE, 4, "eve", day(3), closed=day(14, 23))
    opened(repository, Item.PR, 10, "bob", day(4))
    pull = opened(repository, Item.PR, 11, "dot", day(9), closed=day(13), merged=True)
    said(pull, "bob", day(12), kind=Event.REVIEW)
    opened(repository, Item.PR, 12, "dot", day(10), closed=day(20))
    opened(repository, Item.PR, 13, "dependabot[bot]", day(11), bot=True)
    return repository


def test_issues_of_the_week_next_to_the_week_before(week):
    """Opened, closed, contributions and new contributors of issues, each with the week before."""
    found = stats.kind_trend(Repository.objects.all(), Item.ISSUE, SINCE, UNTIL, NOW)
    assert found.opened == Change(2, 2)
    assert found.closed == Change(2, 0), "closed in the week, also #4 opened before"
    assert found.merged is None, "issues are not merged"
    assert found.contributions == Change(3, 2), "the comment of the bot is not counted"
    assert found.contributors == Change(3, 2), "Ann and ann are one person"
    assert found.newcomers == Change(2, 2)
    assert found.newcomer_logins == ("bob", "cid"), "ann contributed before"


def test_pull_requests_of_the_week(week):
    """Merged and closed without merging are apart; bots are no contributors."""
    found = stats.kind_trend(Repository.objects.all(), Item.PR, SINCE, UNTIL, NOW)
    assert found.opened == Change(3, 1), "the pull request of the bot is opened, too"
    assert found.merged == Change(1, 0), "#11 merged in the week"
    assert found.closed == Change(0, 0), "#12 closed without merging after the week"
    later = stats.kind_trend(Repository.objects.all(), Item.PR, SINCE, day(21), NOW)
    assert (later.closed.now, later.merged.now) == (1, 1), "#12 is closed, not merged"
    assert found.contributions == Change(3, 1)
    assert found.contributors == Change(2, 1)
    assert found.newcomer_logins == ("dot",), "bob opened one before, the bot is no person"


def test_new_contributors_differ_between_issues_and_pull_requests(week):
    """bob opened a pull request before the week, but his first issue is in it."""
    issues = stats.kind_trend(Repository.objects.all(), Item.ISSUE, SINCE, UNTIL, NOW)
    pulls = stats.kind_trend(Repository.objects.all(), Item.PR, SINCE, UNTIL, NOW)
    assert "bob" in issues.newcomer_logins and "bob" not in pulls.newcomer_logins


def test_all_time_has_nothing_to_compare_with(week):
    """Without a start of the time range, there is no time before it."""
    found = stats.kind_trend(Repository.objects.all(), Item.ISSUE, None, None, NOW)
    assert found.opened == Change(4, None)
    assert found.newcomer_logins == ("ann", "bob", "cid", "eve"), "by the handle"


def test_a_range_until_now_is_compared_with_as_long_before(week):
    """The last days end now: the time before is as long."""
    found = stats.kind_trend(Repository.objects.all(), Item.PR, day(9, 0), None, day(16, 0))
    assert found.opened == Change(3, 1)


def test_nothing_in_an_empty_repository():
    """An empty repository has zeros, and a chart without bars."""
    store_repository(repo("o/empty", 0))
    repositories = Repository.objects.all()
    found = stats.kind_trend(repositories, Item.PR, SINCE, UNTIL, NOW)
    assert found.opened == Change(0, 0) and found.newcomer_logins == ()
    assert stats.kind_series(repositories, Item.PR, None, None, NOW, UTC)["labels"] == []


def test_series_per_day(week):
    """A week has a bar per day; what is outside it is left out."""
    found = stats.kind_series(Repository.objects.all(), Item.ISSUE, SINCE, UNTIL, NOW, UTC)
    assert found["size"] == "day"
    assert found["labels"] == [f"2026-01-{d:02d}" for d in range(8, 15)]
    assert found["opened"] == [0, 1, 0, 1, 0, 0, 0]
    assert found["closed"] == [0, 0, 0, 0, 1, 0, 1]
    assert found["contributions"] == [0, 1, 1, 1, 0, 0, 0]
    assert found["newcomers"] == [0, 1, 0, 1, 0, 0, 0]


def test_series_in_the_time_zone_of_the_reader(week):
    """#4 closed at 23:00 UTC on the 14th, which is the 15th in Tokyo: after the week there."""
    tokyo = ZoneInfo("Asia/Tokyo")
    since = datetime(2026, 1, 8, tzinfo=tokyo)
    until = datetime(2026, 1, 15, tzinfo=tokyo)
    found = stats.kind_series(Repository.objects.all(), Item.ISSUE, since, until, NOW, tokyo)
    assert len(found["labels"]) == 7 and sum(found["closed"]) == 1


def test_series_of_all_time_starts_with_the_first_item(week):
    """Without a start, the chart starts with the first item: by week up to half a year."""
    later = datetime(2026, 3, 1, tzinfo=UTC)
    found = stats.kind_series(Repository.objects.all(), Item.PR, None, None, later, UTC)
    assert found["size"] == "week"
    assert found["labels"][0] == "CW 1 2026", (
        "the calendar week of January 4, from Monday 2025-12-29"
    )
    assert sum(found["opened"]) == 4 and sum(found["newcomers"]) == 2


@pytest.mark.parametrize(
    ("days", "size", "bars"),
    [
        (7, "day", 7),
        (30, "day", 30),
        (31, "day", 31),
        (61, "week", 10),
        (90, "week", 14),
        (210, "week", 31),
        (365, "month", 13),
        (2 * 365, "month", 25),
        (5 * 365, "year", 6),
        (3 * 365, "year", 4),
    ],
)
def test_the_length_of_the_bars(days, size, bars):
    """The shortest bars that make at most 31: a week or a month by day, two months by week,
    a year by month, five years by year."""
    end = datetime(2026, 11, 20, tzinfo=UTC)
    start = end - timedelta(days=days)
    assert periods.size_of(start, end) == size
    assert len(periods.buckets(start, end, size, UTC)) == bars


def test_a_month_bucket_over_the_new_year():
    """December is followed by January of the next year."""
    found = periods.buckets(day(1).replace(year=2025, month=12), day(2), "month", UTC)
    assert found == [date(2025, 12, 1), date(2026, 1, 1)]


def test_the_time_before():
    """As long as the time range, just before it."""
    assert periods.previous(SINCE, UNTIL, NOW) == (day(1, 0), SINCE)
    assert periods.previous(None, UNTIL, NOW) is None, "all time until a day: nothing before"


@pytest.mark.parametrize(
    ("change", "difference", "percent"),
    [
        (Change(15, 10), 5, 50.0),
        (Change(5, 10), -5, -50.0),
        (Change(3, 0), 3, None),
        (Change(0, 0), 0, None),
        (Change(3), None, None),
    ],
)
def test_the_change(change, difference, percent):
    """In percent of before; without before or from 0 no percent."""
    assert change.difference == difference
    assert change.percent == percent


def test_series_have_contributors_and_the_part_of_each_bar(week):
    """Each bar has its contributors, each once, and the part of it inside the range."""
    found = stats.kind_series(Repository.objects.all(), Item.ISSUE, SINCE, UNTIL, NOW, UTC)
    assert len(found["contributors"]) == len(found["labels"]) == len(found["exposure"])
    assert all(
        people <= count
        for people, count in zip(found["contributors"], found["contributions"], strict=True)
    )
    assert found["exposure"] == [1.0] * 7
    assert found["merged"] == [], "issues are not merged"


def test_the_length_of_the_bars_can_be_chosen(week):
    """The reader chooses months for a week: one bar; years: one bar."""
    repositories = Repository.objects.all()
    months = stats.kind_series(repositories, Item.ISSUE, SINCE, UNTIL, NOW, UTC, "month")
    assert (months["size"], months["labels"]) == ("month", ["2026-01"])
    years = stats.kind_series(repositories, Item.ISSUE, SINCE, UNTIL, NOW, UTC, "year")
    assert (years["size"], years["labels"], sum(years["opened"])) == ("year", ["2026"], 2)


def test_a_choice_with_too_many_bars_is_replaced(week):
    """Days of ten years would be thousands of bars: the length is chosen instead."""
    since = datetime(2016, 1, 1, tzinfo=UTC)
    found = stats.kind_series(Repository.objects.all(), Item.ISSUE, since, UNTIL, NOW, UTC, "day")
    assert found["size"] == "year"
    unknown = stats.kind_series(Repository.objects.all(), Item.ISSUE, SINCE, UNTIL, NOW, UTC, "x")
    assert unknown["size"] == "day"


def test_weeks_are_calendar_weeks():
    """Weeks start on Monday and are named by their calendar week of ISO 8601."""
    from datetime import date

    assert periods.label(date(2026, 1, 5), "week") == "CW 2 2026"
    assert periods.label(date(2025, 12, 29), "week") == "CW 1 2026", "the week of 1 January"
    assert periods.bucket(date(2026, 1, 1), "week") == date(2025, 12, 29)


def test_calendar_weeks_in_german():
    """KW in German."""
    from datetime import date

    from django.utils import translation

    with translation.override("de"):
        assert periods.label(date(2026, 1, 5), "week") == "KW 2 2026"


def test_years():
    """A year starts on 1 January; the next year follows."""
    from datetime import date

    assert periods.bucket(date(2026, 11, 19), "year") == date(2026, 1, 1)
    assert periods.next_bucket(date(2026, 1, 1), "year") == date(2027, 1, 1)
    assert periods.label(date(2026, 1, 1), "year") == "2026"
