"""The country, region and place of locations, and the languages there."""

import pytest

from community_insights.locations import country_of
from community_insights.locations.horizon import places
from community_insights.locations.languages import languages_of, official, spoken_by
from community_insights.locations.names import country_name, language_name
from community_insights.locations.projection import WIDTH, project


@pytest.mark.parametrize(
    ("location", "country", "region", "city"),
    [
        ("Cardiff, Wales", "GB", "WLS", "Cardiff"),
        ("Cardiff", "GB", "WLS", "Cardiff"),
        ("Wales", "GB", "WLS", ""),
        ("Cymru", "GB", "WLS", ""),
        ("Glasgow, Scotland, UK", "GB", "SCT", "Glasgow"),
        ("London, UK", "GB", "", "London"),
        ("Barcelona", "ES", "CT", "Barcelona"),
        ("Bilbao, Basque Country", "ES", "PV", "Bilbao"),
        ("Madrid, Spain", "ES", "", "Madrid"),
        ("Montréal, Québec", "CA", "QC", "Montréal"),
        ("Leeuwarden", "NL", "FR", "Leeuwarden"),
        ("Bolzano", "IT", "32", "Bolzano"),
        ("Germany", "DE", "", ""),
        ("Portland, OR", "US", "", "Portland"),
        ("Paris, Texas", "US", "", "Paris"),
    ],
)
def test_where_a_location_is(location, country, region, city):
    """The country, the region with languages of its own, and the city."""
    found = places().find(location)
    assert (found.country, found.region, found.city) == (country, region, city)
    assert (found.latitude is not None) == bool(city), "a city has coordinates"


def test_a_city_of_another_country_than_named_is_no_place():
    """Lyon is in France: "Lyon, Germany" is Germany without a place."""
    found = places().find("Lyon, Germany")
    assert (found.country, found.city) == ("DE", "")


def test_country_of_and_find_agree():
    """The column user_country of queries and the page Countries find the same country."""
    for location in ("Berlin and Lisbon", "Somewhere, DE", "Edinburgh, Scotland", "CA"):
        assert country_of(location) == places().find(location).country


@pytest.mark.parametrize("location", ["", "Remote", "the internet", "🌍"])
def test_unknown_locations(location):
    """Nothing known: no country."""
    assert places().find(location) is None


def test_official_languages_of_countries():
    """CLDR: official and official in fact, the most spoken first."""
    assert official("AT") == ("de",)
    assert set(official("CH")) == {"de", "gsw", "fr", "it"}
    assert set(official("BE")) == {"nl", "fr", "de"}
    assert official("ZZ") == ()


def test_regions_have_their_own_languages():
    """Wales is English and Welsh; the rest of the United Kingdom English."""
    assert languages_of("GB", "WLS") == ("en", "cy")
    assert languages_of("GB") == ("en",)
    assert languages_of("ES", "CT") == ("es", "ca")
    assert languages_of("GB", "XX") == ("en",), "an unknown region is the country"


def test_how_many_speak_a_language():
    """The share of the people of a country, also for languages that are not official."""
    assert spoken_by("DE", "de") > 0.9
    assert 0 < spoken_by("DE", "en") < 1
    assert spoken_by("DE", "xx") == 0.0


def test_names_in_the_language_of_the_page():
    """Countries and languages are named in the language of the page."""
    assert country_name("DE", "de") == "Deutschland"
    assert country_name("DE", "es") == "Alemania"
    assert language_name("cy", "de") == "Walisisch"
    assert country_name("DE", "xx-unknown") == "Germany", "English for unknown languages"


def test_the_projection_keeps_the_map_in_its_box():
    """The corners of the world are on the map; the north is at the top."""
    west, _ = project(-180, 0)
    east, _ = project(180, 0)
    assert (west, east) == (0.0, WIDTH)
    assert project(0, 60)[1] < project(0, 0)[1] < project(0, -60)[1]
