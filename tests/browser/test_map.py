"""The map of the page Countries in a real browser: colours, borders, cities, the box below the
map, clicks, small countries, and moving and zooming (docs/explanation/countries.rst)."""

import math
import re

import pytest
from playwright.sync_api import expect

from community_insights.models import Event, Item, Person

# contributors and where they live: Chicago has three, Toulouse one, Wales none in a city,
# Luxembourg one, as a small country; bob of the fake GitHub lives in Berlin
PEOPLE = {
    "ann": "Chicago",
    "bea": "Chicago, IL",
    "cid": "Chicago, USA",
    "dan": "Toulouse, France",
    "eve": "Wales",
    "fay": "Luxembourg",
}
WHITE, BLACK = "rgb(255, 255, 255)", "rgb(0, 0, 0)"
DARK_GREEN, LIGHT_GREEN = "rgb(14, 107, 14)", "rgb(204, 255, 204)"


@pytest.fixture
def world(read):
    """The project o/r with contributors in the United States, Germany, Wales, Luxembourg.

    Args:
        read: The site with the project read.

    Returns:
        The site on the page Countries.
    """
    item = Item.objects.first()
    for login, location in PEOPLE.items():
        Event.objects.create(item=item, actor=login, kind=Event.COMMENT, at=item.created_at)
        Person.objects.update_or_create(login=login, defaults={"location": location})
    read.open_page("Countries")
    expect(read.page.locator("svg[data-map] circle.place")).to_have_count(3)
    return read


def screen_point(page, code: str) -> dict:
    """Where the label point of a country of the map is in the window.

    Args:
        page: The page with the map.
        code: The code of the country.

    Returns:
        x and y in the window.
    """
    return page.evaluate(
        """(code) => {
          const svg = document.querySelector("svg[data-map]");
          const path = svg.querySelector(`path[data-country="${code}"]`);
          const [x, y, w, h] = svg.getAttribute("viewBox").split(" ").map(Number);
          const box = svg.getBoundingClientRect();
          return {
            x: box.left + (Number(path.dataset.x) - x) / w * box.width,
            y: box.top + (Number(path.dataset.y) - y) / h * box.height,
          };
        }""",
        code,
    )


def city_in(page, code: str):
    """The circle of the city of a country nearest to its label point.

    Args:
        page: The page with the map.
        code: The code of the country.

    Returns:
        The locator of the circle.
    """
    index = page.evaluate(
        """(code) => {
          const svg = document.querySelector("svg[data-map]");
          const path = svg.querySelector(`path[data-country="${code}"]`);
          let best = null, distance = Infinity;
          svg.querySelectorAll("circle.place").forEach((c) => {
            const dx = c.cx.baseVal.value - path.dataset.x;
            const d = Math.hypot(dx, c.cy.baseVal.value - path.dataset.y);
            if (d < distance) { distance = d; best = c.dataset.place; }
          });
          return best;
        }""",
        code,
    )
    return page.locator(f'svg[data-map] circle[data-place="{index}"]')


def style_of(page, selector: str, name: str) -> str:
    """A computed style of an element.

    Args:
        page: The page.
        selector: The element.
        name: The property, such as ``fill``.

    Returns:
        The value.
    """
    return page.evaluate(
        "([s, n]) => getComputedStyle(document.querySelector(s))[n]", [selector, name]
    )


def view_box(page) -> list[float]:
    """The view box of the map: the part of the world shown.

    Args:
        page: The page.

    Returns:
        x, y, width and height.
    """
    text = page.locator("svg[data-map]").get_attribute("viewBox") or ""
    return [float(number) for number in text.split()]


def center_of(locator) -> tuple[float, float]:
    """The centre of an element in the window.

    Args:
        locator: The element.

    Returns:
        x and y.
    """
    box = locator.bounding_box()
    return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2


def test_countries_are_black_or_green_with_white_borders(world):
    """Nobody: black; one contributor: dark green; the most: the brightest green."""
    page = world.page
    assert style_of(page, 'path[data-country="BR"]', "fill") == BLACK
    assert style_of(page, 'path[data-country="DE"]', "fill") == DARK_GREEN
    assert style_of(page, 'path[data-country="FR"]', "fill") == DARK_GREEN
    assert style_of(page, 'path[data-country="US"]', "fill") == LIGHT_GREEN
    for code in ("BR", "US"):
        assert style_of(page, f'path[data-country="{code}"]', "stroke") == WHITE
        assert style_of(page, f'path[data-country="{code}"]', "strokeWidth") == "2px"


def test_cities_are_circles_whose_area_grows_with_their_people(world):
    """Chicago (3), Berlin and Toulouse (1): green with a white border; Wales has no city."""
    page = world.page
    chicago = float(city_in(page, "US").get_attribute("r") or 0)
    berlin = float(city_in(page, "DE").get_attribute("r") or 0)
    assert chicago / berlin == pytest.approx(math.sqrt(3)), "area in proportion to people"
    first = "svg[data-map] circle.place"
    assert style_of(page, first, "stroke") == WHITE
    assert style_of(page, first, "strokeWidth") == "2px"
    red, green, blue = (int(n) for n in re.findall(r"\d+", style_of(page, first, "fill")))
    assert green > red and green > blue, "a green middle"
    assert city_in(page, "US").is_visible()


def test_the_box_below_the_map(world):
    """Centred below the map, always the same size: how to use it, a country, a city."""
    page = world.page
    info = page.locator("[data-map-info]")
    country = page.locator("[data-info-country]")
    city = page.locator("[data-info-place]")
    size = info.bounding_box()
    map_box = page.locator("[data-world-map]").bounding_box()
    assert size["y"] == pytest.approx(map_box["y"] + map_box["height"], abs=2), "below the map"
    assert center_of(info)[0] == pytest.approx(map_box["x"] + map_box["width"] / 2, abs=2)
    expect(country).to_contain_text("Point at a country or a city")
    point = screen_point(page, "US")
    page.mouse.move(point["x"], point["y"])
    expect(country).to_have_text("3 contributors from United States")
    expect(city).to_have_text("")
    assert style_of(page, 'path[data-country="US"]', "strokeWidth") == "6px", "3 times as wide"
    page.mouse.move(*center_of(city_in(page, "US")))
    expect(country).to_have_text("3 contributors from United States")
    expect(city).to_have_text("Chicago: 3 contributors")
    point = screen_point(page, "BR")
    page.mouse.move(point["x"], point["y"])
    expect(country).to_have_text("No contributors from Brazil")
    expect(city).to_have_text("")
    assert info.bounding_box()["height"] == size["height"], "always the same size"


def test_a_click_shows_the_country(world):
    """A click opens #country= with the details; the box keeps the country."""
    page = world.page
    point = screen_point(page, "US")
    page.mouse.click(point["x"], point["y"])
    expect(page).to_have_url(re.compile(r"#country=US$"))
    expect(page.locator('[data-country-detail="US"]')).to_be_visible()
    expect(page.locator('[data-country-detail="DE"]')).to_be_hidden()
    expect(page.locator('path[data-country="US"]')).to_have_class(re.compile("chosen"))
    page.mouse.move(1, 1)  # away from the map
    expect(page.locator("[data-info-country]")).to_have_text("3 contributors from United States")


def test_a_click_on_a_city_shows_its_country(world):
    """Berlin is in Germany."""
    page = world.page
    page.mouse.click(*center_of(city_in(page, "DE")))
    expect(page).to_have_url(re.compile(r"#country=DE$"))
    expect(page.locator('[data-country-detail="DE"]')).to_be_visible()


def test_small_countries_are_found_near_their_centre(world):
    """Luxembourg has a dot of its colour and is chosen next to it, on top of its neighbours."""
    page = world.page
    dot = page.locator("svg[data-map] circle.small-country")
    expect(dot).to_have_count(1)
    point = screen_point(page, "LU")
    page.mouse.click(point["x"] + 1, point["y"] + 1)  # near its centre, also on a phone
    expect(page).to_have_url(re.compile(r"#country=LU$"))
    expect(page.locator("[data-info-country]")).to_have_text("1 contributor from Luxembourg")


def test_zoom_and_move_the_map(world):
    """The wheel and the buttons zoom, dragging moves, reset shows the world; no click."""
    page = world.page
    whole = view_box(page)
    svg = page.locator("svg[data-map]")
    x, y = center_of(svg)
    page.mouse.move(x, y)
    page.mouse.wheel(0, -400)
    expect(svg).not_to_have_attribute("viewBox", " ".join(f"{n:g}" for n in whole))
    zoomed = view_box(page)
    assert zoomed[2] < whole[2] / 1.5, "zoomed in"
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x - 120, y, steps=6)
    page.mouse.up()
    moved = view_box(page)
    assert moved[0] > zoomed[0] and moved[2] == pytest.approx(zoomed[2]), "moved east"
    assert "#country=" not in page.url, "a drag chooses no country"
    page.get_by_role("button", name="Show the whole world").click()
    assert view_box(page) == whole
    page.get_by_role("button", name="Zoom in").click()
    assert view_box(page)[2] == pytest.approx(whole[2] * 0.6)
    page.get_by_role("button", name="Zoom out").click()
    page.get_by_role("button", name="Zoom out").click()
    assert view_box(page)[2] == pytest.approx(whole[2]), "never more than the world"
    world.does_not_scroll_sideways()
