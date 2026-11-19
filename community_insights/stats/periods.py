"""The time before a time range, and the days, weeks or months that split a range for a chart."""

from datetime import date, datetime, timedelta, tzinfo

from django.utils import timezone

DAY, WEEK, MONTH = "day", "week", "month"
MOST_DAYS = 31  # up to this many days, a chart has a bar per day
MOST_WEEKS = 26 * 7  # up to this many days (half a year), a bar per week; longer per month


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


def size_of(start: datetime, end: datetime) -> str:
    """How long the bars of a chart from start to end are: a day, a week or a month.

    Args:
        start: The start of the chart.
        end: The end of the chart.

    Returns:
        ``day`` up to a month, ``week`` up to half a year, else ``month``.

    Examples:
        >>> from datetime import UTC
        >>> start = datetime(2026, 1, 1, tzinfo=UTC)
        >>> [size_of(start, start + timedelta(days=d)) for d in (7, 90, 365)]
        ['day', 'week', 'month']
    """
    days = (end - start).total_seconds() / 86400
    if days <= MOST_DAYS:
        return DAY
    if days <= MOST_WEEKS:
        return WEEK
    return MONTH


def bucket(day: date, size: str) -> date:
    """The first day of the day, week (from Monday) or month that a day is in.

    Args:
        day: The day.
        size: ``day``, ``week`` or ``month``.

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
    return day


def buckets(start: datetime, end: datetime, size: str, tz: tzinfo) -> list[date]:
    """The first days of all days, weeks or months from start to end, without a gap.

    Args:
        start: The start of the chart.
        end: The end of the chart, excluded.
        size: ``day``, ``week`` or ``month``.
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
        day = found[-1]
        if size == MONTH:
            found.append(date(day.year + day.month // 12, day.month % 12 + 1, 1))
        else:
            found.append(day + timedelta(days=7 if size == WEEK else 1))
    return found


def label(day: date, size: str) -> str:
    """The label of a bar on the time axis of a chart.

    Args:
        day: The first day of the bar.
        size: ``day``, ``week`` or ``month``.

    Returns:
        The day, such as ``2026-11-16``, for a week its Monday; a month as ``2026-11``.

    Examples:
        >>> label(date(2026, 11, 16), "week"), label(date(2026, 11, 1), "month")
        ('2026-11-16', '2026-11')
    """
    return day.strftime("%Y-%m") if size == MONTH else day.isoformat()


def count_by(times, start: datetime, end: datetime, size: str, tz: tzinfo) -> list[int]:
    """How many of the times fall in each day, week or month from start to end.

    Args:
        times: Aware times; those outside the range are left out.
        start: The start of the chart.
        end: The end of the chart, excluded.
        size: ``day``, ``week`` or ``month``.
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
