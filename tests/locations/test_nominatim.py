"""Nominatim, the search of OpenStreetMap, faked: the tests do not use the network."""

import httpx
import pytest

from community_insights.locations import nominatim
from community_insights.locations.nominatim import Nominatim

CARDIFF = {
    "lat": "51.48",
    "lon": "-3.18",
    "addresstype": "city",
    "name": "Cardiff",
    "address": {"country_code": "gb", "ISO3166-2-lvl4": "GB-WLS"},
}


def server(answer, asked=None):
    """A fake Nominatim.

    Args:
        answer: The answer: a list of results, or a status code.
        asked: A list to which each request is added.

    Returns:
        The client.
    """

    def handle(request: httpx.Request) -> httpx.Response:
        """Answer as the table says."""
        if asked is not None:
            asked.append(request)
        if isinstance(answer, int):
            return httpx.Response(answer)
        return httpx.Response(200, json=answer)

    return httpx.Client(transport=httpx.MockTransport(handle))


@pytest.fixture(autouse=True)
def no_pause(monkeypatch):
    """The pauses between requests take no time; they are counted."""
    pauses = []
    monkeypatch.setattr(nominatim.time, "sleep", pauses.append)
    return pauses


def test_a_city_with_its_region(no_pause):
    """A city is a place on the map; Wales is a region with its languages."""
    asked = []
    found = Nominatim("https://osm.example", server([CARDIFF], asked)).search("Caerdydd")
    assert (found.country, found.region, found.city, found.source) == (
        "GB",
        "WLS",
        "Cardiff",
        "nominatim",
    )
    assert (found.latitude, found.longitude) == (51.48, -3.18)
    params = asked[0].url.params
    assert asked[0].url.path == "/search" and params["q"] == "Caerdydd"
    assert params["format"] == "jsonv2" and params["limit"] == "1"


def test_the_client_names_the_software():
    """The usage policy asks for a User-Agent that names the software, nobody's address."""
    client = Nominatim("https://osm.example").client
    assert client.headers["User-Agent"] == nominatim.USER_AGENT
    assert "@" not in nominatim.USER_AGENT


def test_at_most_one_request_a_second(no_pause):
    """The second request waits for the rest of the second."""
    search = Nominatim("https://osm.example", server([CARDIFF]))
    search.search("a")
    search.search("b")
    assert len(no_pause) == 1 and 0 < no_pause[0] <= 1


def test_a_country_or_a_state_is_no_place():
    """A whole country has no dot on the map."""
    result = {"lat": "51", "lon": "10", "addresstype": "country", "address": {"country_code": "de"}}
    found = Nominatim("https://osm.example", server([result])).search("Deutschland")
    assert (found.country, found.city, found.latitude) == ("DE", "", None)


@pytest.mark.parametrize(
    "answer",
    [
        [],
        500,
        429,
        {"error": "no list"},
        [{"address": {}}],
        [{"address": {"country_code": "europe"}}],
    ],
)
def test_nothing_found_or_an_error(answer):
    """Nothing, a failure or an answer without a country: None, the fetch goes on."""
    assert Nominatim("https://osm.example", server(answer)).search("x") is None


def test_a_place_without_coordinates_keeps_its_country():
    """Broken coordinates: the country without a dot."""
    result = dict(CARDIFF, lat="north")
    found = Nominatim("https://osm.example", server([result])).search("x")
    assert (found.country, found.region, found.city) == ("GB", "WLS", "")


def test_no_answer_at_all():
    """A server that cannot be reached: None."""

    def refuse(request):
        """Fail to connect."""
        raise httpx.ConnectError("no", request=request)

    client = httpx.Client(transport=httpx.MockTransport(refuse))
    assert Nominatim("https://osm.example", client).search("x") is None
