"""Images kept until the data changes: ETag, 304 Not Modified and the cache (views/stamped.py)."""

from zoneinfo import ZoneInfo

import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.test import RequestFactory
from django.utils import timezone, translation

from community_insights import charts, data_stamp
from community_insights.models import Item, Project, Repository
from community_insights.views import stamped

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _empty_cache():
    """Each test starts without kept images."""
    cache.clear()


def chart_url():
    """The address of a chart of the project."""
    return f"/s/{Project.objects.get().pk}/chart/responses-pr.svg?theme=dark"


def test_the_same_data_gives_the_same_etag(synced, signed_in):
    """The same chart of the same data has the same ETag."""
    first = signed_in.get(chart_url())
    second = signed_in.get(chart_url())
    assert first.status_code == second.status_code == 200
    assert first["ETag"] == second["ETag"]
    assert first.content == second.content


def test_a_browser_with_the_image_gets_304(synced, signed_in):
    """A browser that has the image gets 304 Not Modified, without the image."""
    etag = signed_in.get(chart_url())["ETag"]
    again = signed_in.get(chart_url(), HTTP_IF_NONE_MATCH=etag)
    assert again.status_code == 304
    assert again["ETag"] == etag
    assert not again.content


def test_another_etag_gets_the_image(synced, signed_in):
    """An ETag of older data gets the image."""
    answer = signed_in.get(chart_url(), HTTP_IF_NONE_MATCH='"older"')
    assert answer.status_code == 200 and answer.content


def test_the_browser_keeps_it_but_asks(synced, signed_in):
    """The browser may keep the image, but asks each time: no-cache, never no-store."""
    control = signed_in.get(chart_url())["Cache-Control"]
    assert "no-cache" in control and "private" in control
    assert "no-store" not in control and "max-age=0" not in control


def test_a_kept_image_is_not_drawn_again(synced, signed_in, monkeypatch):
    """The second time the image comes from the cache."""
    drawn = []
    original = charts.response_chart

    def counting(*args, **kwargs):
        """Draw the chart and count it."""
        drawn.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(charts, "response_chart", counting)
    signed_in.get(chart_url())
    signed_in.get(chart_url())
    assert len(drawn) == 1


def test_changed_data_gives_a_new_etag(synced, signed_in):
    """A change of the data, such as a fetch, gives a new ETag and a new image."""
    etag = signed_in.get(chart_url())["ETag"]
    Item.objects.filter(number=1).update(title="changed")
    answer = signed_in.get(chart_url(), HTTP_IF_NONE_MATCH=etag)
    assert answer.status_code == 200
    assert answer["ETag"] != etag


def test_the_next_hour_gives_a_new_etag(synced, signed_in, monkeypatch):
    """Waiting times grow without a change of the data: the stamp holds the hour."""
    etag = signed_in.get(chart_url())["ETag"]
    now = data_stamp.time.time()
    monkeypatch.setattr(data_stamp.time, "time", lambda: now + data_stamp.HOUR)
    assert signed_in.get(chart_url())["ETag"] != etag


def test_another_address_is_another_image(synced, signed_in):
    """Another theme is another address: another image."""
    etag = signed_in.get(chart_url())["ETag"]
    assert signed_in.get(chart_url().replace("dark", "light"))["ETag"] != etag


@pytest.mark.parametrize(
    "change",
    [
        lambda request: setattr(request, "user", AnonymousUser()),  # another user
        lambda request: translation.activate("de"),  # another language
        lambda request: timezone.activate(ZoneInfo("America/New_York")),  # another time zone
        lambda request: setattr(request, "path", "/s/1/chart/hours.svg"),  # another address
    ],
)
def test_the_key_holds_what_the_image_depends_on(user, change):
    """Who asks, in which language and time zone, for which address: each is another key."""
    request = RequestFactory().get("/s/1/chart/responses-pr.svg")
    request.user = user
    timezone.activate(ZoneInfo("Asia/Tokyo"))
    try:
        before = stamped.key(request, "chart", "stamp")
        change(request)
        assert stamped.key(request, "chart", "stamp") != before
    finally:
        timezone.deactivate()


def test_the_key_holds_the_view_and_the_stamp(user):
    """The SVG and the JSON of a chart, or older data, have other keys."""
    request = RequestFactory().get("/s/1/chart/responses-pr.svg")
    request.user = user
    key = stamped.key(request, "chart", "stamp")
    assert key == stamped.key(request, "chart", "stamp")
    assert key != stamped.key(request, "chart_json", "stamp")
    assert key != stamped.key(request, "chart", "older")


def test_without_cachalot_nothing_is_kept(synced, signed_in, settings):
    """Without cachalot no change is noted: the image is drawn each time, never kept."""
    settings.CACHALOT_ENABLED = False
    answer = signed_in.get(chart_url())
    assert answer.status_code == 200
    assert not answer.has_header("ETag")
    assert "no-store" in answer["Cache-Control"]


def test_errors_are_not_kept(synced, signed_in):
    """A chart that does not exist is not kept and has no ETag."""
    answer = signed_in.get(f"/s/{Project.objects.get().pk}/chart/nothing.svg")
    assert answer.status_code == 404
    assert not answer.has_header("ETag")


def test_a_badge_keeps_its_15_minutes(synced, client):
    """A badge keeps its time for the proxies of GitHub, and has an ETag."""
    url = f"/badge/{Project.objects.get().badge_token}.svg"
    answer = client.get(url)
    assert answer["Cache-Control"] == "public, max-age=900"
    assert answer.has_header("ETag")
    again = client.get(url, HTTP_IF_NONE_MATCH=answer["ETag"])
    assert again.status_code == 304
    assert again["Cache-Control"] == "public, max-age=900"


def test_only_get_is_kept(synced, signed_in):
    """Another method is answered by the view, without an ETag."""
    answer = signed_in.post(chart_url())
    assert not answer.has_header("ETag")


def test_pages_do_not_change_the_data(synced, signed_in):
    """Looking at pages writes no table, so the stamp stays: they would change it each time."""
    pk = Project.objects.get().pk
    pages = [f"/s/{pk}/", f"/s/{pk}/contributors/", f"/s/{pk}/people/bob/", chart_url()]
    for page in pages:
        signed_in.get(page)
    stamp = data_stamp.stamp()
    for page in pages:
        assert signed_in.get(page).status_code == 200
    assert data_stamp.stamp() == stamp
    assert Repository.objects.count() == 1
