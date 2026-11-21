"""The pages Countries and Languages: where the contributors are from and what they speak."""

import json
import re
from datetime import UTC, datetime

import pytest

from community_insights import stats
from community_insights.models import Event, Item, Location, Person, Project, Repository
from community_insights.views.geography import color
from tests.data import T0

pytestmark = pytest.mark.django_db

PEOPLE = {
    "bob": "Berlin",  # from the fixture synced
    "carol": "Cardiff, Wales",
    "dave": "Vienna, Austria",
    "maint": "Mars",
}


@pytest.fixture
def pk(synced):
    """The project of the synced repository; its people live in Germany, Wales, Austria."""
    for login, location in PEOPLE.items():
        Person.objects.update_or_create(login=login, defaults={"location": location})
    Person.objects.update_or_create(
        login="ci[bot]", defaults={"location": "Berlin", "is_bot": True}
    )
    return Project.objects.get().pk


def page(client, pk, query=""):
    """The page Countries as text.

    Args:
        client: The client.
        pk: The project.
        query: The parameters.

    Returns:
        The HTML.
    """
    return client.get(f"/s/{pk}/countries/{query}").content.decode()


def test_contributors_mapped(pk, signed_in):
    """3 of 4 contributors have a known country; the bot is no contributor."""
    text = page(signed_in, pk)
    assert 'data-mapped="3/4"' in text
    assert "<strong>3/4</strong> contributors mapped" in text
    assert "the location of 1 contributor names no known country" in text
    assert re.search(r"data-unknown>.*maint.*Mars", text, re.S)


def test_the_list_colours_and_tips_of_the_countries(pk, signed_in):
    """Each country with its count, its shade and its tool tip, linked to #country=."""
    text = page(signed_in, pk)
    for code, name in (("DE", "Germany"), ("GB", "United Kingdom"), ("AT", "Austria")):
        assert f'data-country="{code}" data-count="1" data-color="#0e6b0e"' in text
        assert f'data-tip="1 contributor from {name}"' in text
        assert f'href="#country={code}"' in text


def test_the_map_and_its_data(pk, signed_in):
    """The SVG to load, the dots of the places and the names of all countries."""
    text = page(signed_in, pk)
    assert 'data-src="/static/maps/world.svg"' in text
    places = json.loads(
        re.search(r"data-places=\"([^\"]*)\"", text).group(1).replace("&quot;", '"')
    )
    assert sorted(p[2:] for p in places) == [
        ["AT", 1, "Vienna: 1 contributor", "Vienna"],
        ["DE", 1, "Berlin: 1 contributor", "Berlin"],
        ["GB", 1, "Cardiff: 1 contributor", "Cardiff"],
    ]
    assert all(0 <= p[0] <= 1000 and 0 <= p[1] <= 500 for p in places)
    names = json.loads(re.search(r"data-names=\"([^\"]*)\"", text).group(1).replace("&quot;", '"'))
    assert names["FR"] == "France", "the gray countries are named in their tool tips"
    assert 'data-nobody="No contributors from {country}"' in text
    assert "js/country-map.js" in text
    box = re.search(r"<div[^>]*data-map-info.*?</div>\s*</div>", text, re.S).group(0)
    assert "Point at a country or a city" in box, "how to use the map, until something is chosen"
    assert "data-info-place" in box


def test_the_details_of_a_country(pk, signed_in):
    """Below the map: the contributors, their locations, the time and the languages."""
    text = page(signed_in, pk)
    wales = re.search(r'<section[^>]*data-country-detail="GB".*?</section>', text, re.S).group(0)
    assert 'id="country-GB"' in wales
    assert re.search(
        r'<tbody data-city="Cardiff">.*carol</a></td><td>Cardiff, Wales</td>', wales, re.S
    )
    assert "data-languages>English, Welsh<" in wales, "Wales is English and Welsh"
    assert "data-first>2026-01-06<" in wales and "data-last>2026-01-06<" in wales


def test_the_time_range_chooses_the_contributors(pk, signed_in):
    """Only who contributed in the time range: dave commented on the 7th (Tokyo)."""
    text = page(signed_in, pk, "?since=2026-01-07&until=2026-01-07")
    assert 'data-mapped="1/1"' in text and 'data-country="AT"' in text
    assert 'data-country="DE"' not in text


def test_nobody_in_the_time(pk, signed_in):
    """No contributors: a page that says so, the map still gray."""
    text = page(signed_in, pk, "?since=2026-03-01&until=2026-03-07")
    assert 'data-mapped="0/0"' in text
    assert "No contributor of this time has a location with a known country." in text


def test_the_place_kept_in_the_database_is_used(pk, signed_in):
    """A location found by Nominatim is used, also where GeoNames finds something else."""
    Location.objects.create(
        text="Mars",
        country="FR",
        city="Marseille",
        latitude=43.3,
        longitude=5.4,
        source="nominatim",
    )
    text = page(signed_in, pk)
    assert 'data-mapped="4/4"' in text and 'data-country="FR"' in text
    assert "Marseille: 1 contributor" in text


def test_the_page_in_german(pk, signed_in):
    """Names of countries and languages in the language of the page."""
    text = signed_in.get(f"/s/{pk}/countries/", HTTP_ACCEPT_LANGUAGE="de").content.decode()
    assert "Vereinigtes Königreich" in text and "Englisch, Walisisch" in text
    assert "Beitragende zugeordnet" in text


def test_visitors_see_public_repositories(pk, client):
    """A public repository has the pages for everybody; projects need a sign in."""
    assert client.get("/s/o~r/countries/").status_code == 200
    assert client.get("/s/o~r/languages/").status_code == 200
    assert client.get(f"/s/{pk}/countries/").status_code == 302


def test_the_languages_ranked_by_contributors(pk, signed_in):
    """English: Wales; German: Germany and Austria; Welsh: Wales; with the countries."""
    text = signed_in.get(f"/s/{pk}/languages/").content.decode()
    rows = re.findall(r'<tr data-language="([a-z_A-Z]+)">', text)
    assert rows[0] == "de", "two contributors: Germany and Austria"
    assert set(rows) == {"de", "en", "cy"}
    german = re.search(r'<tr data-language="de">.*?</tr>', text, re.S).group(0)
    assert "#country=DE" in german and "#country=AT" in german
    assert "67 %" in german, "2 of 3 mapped contributors"
    assert "Welsh" in text and "Nobody is asked what they speak." in text


def test_languages_without_anybody(signed_in, pk):
    """No contributors: the page says so."""
    text = signed_in.get(f"/s/{pk}/languages/?since=2026-03-01&until=2026-03-07").content.decode()
    assert "No contributor of this time has a location with a known country." in text


def test_the_pages_are_in_the_menu(pk, signed_in):
    """Countries and Languages follow Contributors in the menu of the pages."""
    text = page(signed_in, pk)
    assert f'href="/s/{pk}/countries/"' in text and f'href="/s/{pk}/languages/"' in text


@pytest.mark.parametrize(
    ("count", "most", "shade"),
    [
        (0, 0, "#000000"),
        (0, 50, "#000000"),
        (1, 1, "#0e6b0e"),
        (1, 100, "#0e6b0e"),
        (10, 100, "#6db56d"),
        (100, 100, "#ccffcc"),
        (200, 100, "#ccffcc"),
    ],
)
def test_the_colours_of_the_heat_map(count, most, shade):
    """Black for nobody, dark green for one, light green for the most, logarithmic between."""
    assert color(count, most) == shade


def test_the_legend_of_the_colours(pk, signed_in):
    """The legend names black and the range of the greens."""
    text = page(signed_in, pk)
    legend = re.search(r"<p[^>]*data-legend>.*?</p>", text, re.S).group(0)
    assert "legend-nobody" in legend and "legend-scale" in legend
    assert "from 1 to 1 contributor" in legend


def test_country_map_of_several_people_in_one_place(synced):
    """Two people in Berlin are one dot with two; handles differ only in case."""
    Person.objects.update_or_create(login="bob", defaults={"location": "Berlin"})
    Person.objects.update_or_create(login="carol", defaults={"location": "berlin"})
    found = stats.country_map(Repository.objects.all(), None, None)
    germany = found.countries[0]
    assert germany.code == "DE" and germany.count == 2
    assert [p[0] for p in germany.people] == ["bob", "carol"], "sorted by handle"
    assert [(p[2], p[4]) for p in found.places] == [("Berlin", 2)]
    assert germany.first == datetime.fromisoformat(T0), "bob opened the first"
    assert germany.last == datetime(2026, 1, 6, 9, tzinfo=UTC), "carol opened the last"


def test_a_person_with_two_spellings_is_one_contributor(synced):
    """Events by Bob and bob count once."""
    issue = Item.objects.filter(kind=Item.ISSUE).first()
    Event.objects.create(item=issue, actor="Bob", kind=Event.COMMENT, at="2026-01-08T00:00:00Z")
    found = stats.country_map(Repository.objects.all(), None, None)
    assert found.contributors == 4


def test_the_people_of_a_country_are_grouped_by_city(pk, signed_in):
    """The biggest city first, those without a city last, each with its number."""
    for login, location in (("eve", "Munich"), ("fay", "Munich, Germany"), ("gus", "Germany")):
        Person.objects.update_or_create(login=login, defaults={"location": location})
        issue = Item.objects.filter(kind=Item.ISSUE).first()
        Event.objects.create(item=issue, actor=login, kind=Event.COMMENT, at=issue.created_at)
    text = page(signed_in, pk)
    germany = re.search(r'<section[^>]*data-country-detail="DE".*?</section>', text, re.S).group(0)
    cities = re.findall(r'<tbody data-city="([^"]*)">', germany)
    assert cities == ["Munich", "Berlin", ""], "the most first, without a city last"
    munich = re.search(r'<tbody data-city="Munich">.*?</tbody>', germany, re.S).group(0)
    assert "2 contributors" in munich and "eve</a>" in munich and "fay</a>" in munich
    assert "Without a city or place" in germany
    places = json.loads(
        re.search(r"data-places=\"([^\"]*)\"", text).group(1).replace("&quot;", '"')
    )
    assert ["DE", 2, "Munich: 2 contributors", "Munich"] in [p[2:] for p in places]
