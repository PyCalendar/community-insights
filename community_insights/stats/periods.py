"""The time before a time range, and the days, weeks, months or years that split it for a chart."""

from datetime import UTC, date, datetime, timedelta, tzinfo

from django.utils import timezone
from django.utils.translation import gettext

DAY, WEEK, MONTH, YEAR = "day", "week", "month", "year"
SIZES = (DAY, WEEK, MONTH, YEAR)
MOST_BARS = 31  # a chart has at most so many bars: the shortest bars that fit


def previous(
    since: datetime | None, until: datetime | None, now: datetime
) -> tuple[datetime, datetime] | None:
    """The period of the same length just before the time range, to compare with.

    Args:
        since: The start of the time range, None for the beginning.
        until: The end of the time range, excluded; None for now.
        now: The time now, the end of a range without one.

    Returns:
        The start and the end (excluded) of the period before; None without a start, as all
        time has nothing before it.

    Examples:
        >>> from datetime import UTC
        >>> start, end = previous(datetime(2026, 1, 8, tzinfo=UTC), None,
        ...                       datetime(2026, 1, 15, tzinfo=UTC))
        >>> start.day, end.day
        (1, 8)
        >>> previous(None, None, datetime(2026, 1, 15, tzinfo=UTC)) is None
        True
    """
    if since is None:
        return None
    end = until or now
    return since - (end - since), since


def size_of(start: datetime, end: datetime, tz: tzinfo = UTC) -> str:
    """How long the bars of a chart from start to end are: the shortest with few enough bars.

    Days, weeks, months or years: the first of them that splits the time into at most
    ``MOST_BARS`` bars. A week or a month has days, two months weeks, a year months and
    five years years.

    Args:
        start: The start of the chart.
        end: The end of the chart, excluded.
        tz: The time zone of the days.

    Returns:
        ``day``, ``week``, ``month`` or ``year``.

    Examples:
        >>> start = datetime(2026, 1, 1, tzinfo=UTC)
        >>> [size_of(start, start + timedelta(days=d)) for d in (7, 31, 61, 365, 5 * 365)]
        ['day', 'day', 'week', 'month', 'year']
    """
    for size in (DAY, WEEK, MONTH):
        if len(buckets(start, end, size, tz)) <= MOST_BARS:
            return size
    return YEAR


def bucket(day: date, size: str) -> date:
    """The first day of the day, week (from Monday) or month that a day is in.

    Args:
        day: The day.
        size: ``day``, ``week``, ``month`` or ``year``.

    Returns:
        The first day.

    Examples:
        >>> bucket(date(2026, 11, 19), "week"), bucket(date(2026, 11, 19), "month")
        (datetime.date(2026, 11, 16), datetime.date(2026, 11, 1))
    """
    if size == WEEK:
        return day - timedelta(days=day.weekday())
    if size == MONTH:
        return day.replace(day=1)
    if size == YEAR:
        return day.replace(month=1, day=1)
    return day


def buckets(start: datetime, end: datetime, size: str, tz: tzinfo) -> list[date]:
    """The first days of all days, weeks or months from start to end, without a gap.

    Args:
        start: The start of the chart.
        end: The end of the chart, excluded.
        size: ``day``, ``week``, ``month`` or ``year``.
        tz: The time zone of the days.

    Returns:
        The first days, in order; at least one.

    Examples:
        >>> from datetime import UTC
        >>> buckets(datetime(2026, 1, 30, tzinfo=UTC), datetime(2026, 3, 2, tzinfo=UTC),
        ...         "month", UTC)
        [datetime.date(2026, 1, 1), datetime.date(2026, 2, 1), datetime.date(2026, 3, 1)]
    """
    first = bucket(timezone.localtime(start, tz).date(), size)
    # the end is excluded: a range until midnight ends with the day before
    last = bucket(timezone.localtime(end - timedelta(microseconds=1), tz).date(), size)
    found = [first]
    while found[-1] < last:
        found.append(next_bucket(found[-1], size))
    return found


def label(day: date, size: str) -> str:
    """The label of a bar on the time axis of a chart.

    Args:
        day: The first day of the bar.
        size: ``day``, ``week``, ``month`` or ``year``.

    Returns:
        A day as ``2026-11-16``; a week as its calendar week of ISO 8601, which starts on
        Monday, such as ``CW 47 2026`` (translated, KW in German); a month as ``2026-11``; a
        year as ``2026``.

    Examples:
        >>> label(date(2026, 11, 16), "week"), label(date(2026, 11, 1), "month")
        ('CW 47 2026', '2026-11')
        >>> label(date(2026, 12, 28), "week"), label(date(2026, 1, 1), "year")
        ('CW 53 2026', '2026')
    """
    if size == WEEK:
        year, week, _ = day.isocalendar()
        return gettext("CW %(week)s %(year)s") % {"week": week, "year": year}
    if size == MONTH:
        return day.strftime("%Y-%m")
    if size == YEAR:
        return str(day.year)
    return day.isoformat()


def count_by(times, start: datetime, end: datetime, size: str, tz: tzinfo) -> list[int]:
    """How many of the times fall in each day, week or month from start to end.

    Args:
        times: Aware times; those outside the range are left out.
        start: The start of the chart.
        end: The end of the chart, excluded.
        size: ``day``, ``week``, ``month`` or ``year``.
        tz: The time zone of the days.

    Returns:
        A number for each of ``buckets(start, end, size, tz)``.

    Examples:
        >>> from datetime import UTC
        >>> start, end = datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 4, tzinfo=UTC)
        >>> count_by([datetime(2026, 1, 2, 5, tzinfo=UTC)] * 2, start, end, "day", UTC)
        [0, 2, 0]
    """
    days = buckets(start, end, size, tz)
    index = {day: i for i, day in enumerate(days)}
    counted = [0] * len(days)
    for at in times:
        if start <= at < end:
            counted[index[bucket(timezone.localtime(at, tz).date(), size)]] += 1
    return counted


def next_bucket(day: date, size: str) -> date:
    """The first day of the day, week, month or year after the one that starts with a day.

    Args:
        day: The first day of a bar.
        size: ``day``, ``week``, ``month`` or ``year``.

    Returns:
        The first day of the next bar.

    Examples:
        >>> next_bucket(date(2026, 12, 1), "month"), next_bucket(date(2026, 11, 16), "week")
        (datetime.date(2027, 1, 1), datetime.date(2026, 11, 23))
    """
    if size == MONTH:
        return date(day.year + day.month // 12, day.month % 12 + 1, 1)
    if size == YEAR:
        return date(day.year + 1, 1, 1)
    return day + timedelta(days=7 if size == WEEK else 1)


def exposure(start: datetime, end: datetime, size: str, tz: tzinfo) -> list[float]:
    """The part of each day, week or month from start to end that is inside the range.

    A week that started before the range, or has not ended yet, is only a part of a week:
    the trend of the counts takes that into account.

    Args:
        start: The start of the chart.
        end: The end of the chart, excluded.
        size: ``day``, ``week``, ``month`` or ``year``.
        tz: The time zone of the days.

    Returns:
        A number from 0 to 1 for each of ``buckets(start, end, size, tz)``.

    Examples:
        >>> from datetime import UTC
        >>> start = datetime(2026, 1, 1, 12, tzinfo=UTC)
        >>> exposure(start, datetime(2026, 1, 3, tzinfo=UTC), "day", UTC)
        [0.5, 1.0]
    """
    found = []
    for day in buckets(start, end, size, tz):
        first = timezone.make_aware(datetime.combine(day, datetime.min.time()), tz)
        after = timezone.make_aware(
            datetime.combine(next_bucket(day, size), datetime.min.time()), tz
        )
        inside = min(end, after) - max(start, first)
        found.append(max(0.0, inside / (after - first)))
    return found


def people_by(events, start: datetime, end: datetime, size: str, tz: tzinfo) -> list[int]:
    """How many people contributed in each day, week or month from start to end.

    Args:
        events: The handle and the time of each contribution; handles in any case.
        start: The start of the chart.
        end: The end of the chart, excluded.
        size: ``day``, ``week``, ``month`` or ``year``.
        tz: The time zone of the days.

    Returns:
        A number for each of ``buckets(start, end, size, tz)``: each person once.

    Examples:
        >>> from datetime import UTC
        >>> start, end = datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 3, tzinfo=UTC)
        >>> at = datetime(2026, 1, 2, 5, tzinfo=UTC)
        >>> people_by([("Ann", at), ("ann", at), ("bo", at)], start, end, "day", UTC)
        [0, 2]
    """
    days = buckets(start, end, size, tz)
    index = {day: i for i, day in enumerate(days)}
    found: list[set[str]] = [set() for _ in days]
    for login, at in events:
        if start <= at < end:
            found[index[bucket(timezone.localtime(at, tz).date(), size)]].add(login.lower())
    return [len(people) for people in found]
