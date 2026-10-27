"""The country of a location as people write it in their GitHub profile."""

import pytest

from community_insights.locations import HORIZON_EUROPE, country_of, in_horizon_europe
from community_insights.locations.places import plain


@pytest.mark.parametrize(
    ("location", "country"),
    [
        ("Berlin, Germany", "DE"),
        ("berlin", "DE"),
        ("Lyon", "FR"),
        ("Paris", "FR"),
        ("Zürich", "CH"),
        ("zurich", "CH"),
        ("München", "DE"),
        ("Warszawa", "PL"),
        ("Delft, NL", "NL"),
        ("Vienna / Austria", "AT"),
        ("Kyiv", "UA"),
        ("Portland, OR", "US"),
        ("Cambridge, MA", "US"),
        ("San Francisco, CA", "US"),
        ("Toronto, Canada", "CA"),
        ("CA", "CA"),
        ("USA", "US"),
        ("UK", "GB"),
        ("Edinburgh, Scotland", "GB"),
        ("Deutschland", "DE"),
        ("Türkiye", "TR"),
        ("São Paulo, Brazil", "BR"),
        ("Hamburg (Germany)", "DE"),
        ("Oslo | Norway", "NO"),
        ("Tokyo", "JP"),
        ("Berlin and Lisbon", "PT"),  # the last part that is known
    ],
)
def test_country_of_a_location(location, country):
    assert country_of(location) == country


@pytest.mark.parametrize(
    "location", ["", "   ", "Remote", "Earth", "the internet", ",,,", "localhost", "ZZ", "🌍"]
)
def test_unknown_locations_have_no_country(location):
    assert country_of(location) is None


def test_a_code_alone_is_a_country_not_a_state():
    assert country_of("DE") == "DE"
    assert country_of("Somewhere, DE") == "US"  # Delaware after a place


def test_names_are_compared_without_case_and_accents():
    assert plain("  ÖSTERREICH ") == "osterreich"
    assert country_of("OSTERREICH") == "AT"


@pytest.mark.parametrize(
    ("location", "inside"),
    [
        ("Berlin", True),
        ("Oslo, Norway", True),
        ("London", True),
        ("Kyiv", True),
        ("Toronto", True),
        ("Tokyo", True),
        ("New York", False),
        ("Bangalore", False),
        ("Moscow", False),
        ("Remote", False),
        ("", False),
    ],
)
def test_in_horizon_europe(location, inside):
    assert in_horizon_europe(location) is inside


def test_horizon_europe_has_the_member_states_and_the_associated_countries():
    assert len(HORIZON_EUROPE) == 27 + 23
    assert {"DE", "FR", "NO", "GB", "CH", "UA", "XK"} <= HORIZON_EUROPE
    assert not {"US", "RU", "CN", "AU", "IN"} & HORIZON_EUROPE
