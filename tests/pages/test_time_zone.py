"""Times in the time zone of the browser."""

from datetime import UTC, datetime

import pytest

from community_insights import stats

pytestmark = pytest.mark.django_db


def test_heatmap_uses_timezone():
    """Heatmap uses timezone."""
    import zoneinfo

    times = [datetime(2026, 1, 5, 23, 30, tzinfo=UTC)]  # Monday 23:30 UTC
    assert stats.by_hour_and_weekday(times, UTC)[0][23] == 1
    tokyo = zoneinfo.ZoneInfo("Asia/Tokyo")  # Tuesday 08:30
    assert stats.by_hour_and_weekday(times, tokyo)[1][8] == 1


@pytest.mark.parametrize("zone", ["Not/AZone", "../../etc", "", "UTC", "Asia/Tokyo"])
def test_bad_time_zones_of_the_browser(world, signed_in, zone):  # noqa: F811
    """django-tz-detect stores what the browser sends; a bad one is forgotten."""
    response = signed_in.post("/tz_detect/set/", {"timezone": zone})
    assert response.status_code in (200, 400)
    page = signed_in.get(f"/s/{world['project'].pk}/people/bob/")
    assert page.status_code == 200
    # an empty one is refused and the zone set before stays
    shown = "Asia/Tokyo" if zone in ("Asia/Tokyo", "") else "UTC"
    assert f'data-time-zone="{shown}"'.encode() in page.content
