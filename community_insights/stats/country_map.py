"""Where the contributors are from: countries and places, for the page Countries."""

from dataclasses import dataclass
from datetime import datetime

from ..locations.languages import languages_of
from ..locations.locator import known
from ..locations.projection import project
from ..models import Event, Person
from .country_stats import CountryStats
from .selection import events_in


@dataclass(frozen=True)
class CountryMap:
    """The contributors of a time range by the country of their location.

    Attributes:
        contributors: How many people, not bots, contributed in the time range.
        mapped: How many of them have a location whose country is known.
        without_location: How many have no location in their profile, or were not read yet.
        unknown: Who has a location whose country is not known: handle and location.
        countries: The countries with contributors, the most contributors first.
        places: The cities and places of the map: x and y on the map (`projection`), the
            name of the place, the code of the country and how many contributors are there.
    """

    contributors: int
    mapped: int
    without_location: int
    unknown: list[tuple[str, str]]
    countries: list[CountryStats]
    places: list[tuple[float, float, str, str, int]]


def country_map(repositories, since: datetime | None, until: datetime | None) -> CountryMap:
    """Where the people who contributed in a time range are from.

    A contribution is an opening, a comment or a review on a pull request or an issue, as
    on the page Trends. The location is the one of the GitHub profile, found once
    (`locations.locator`).

    Args:
        repositories: The repositories.
        since: The start of the time range, None for the beginning.
        until: The end of the time range, excluded; None for now.

    Returns:
        The contributors by country.
    """
    events = events_in(
        Event.objects.filter(item__repository__in=repositories, is_bot=False).order_by(),
        since,
        until,
    )
    spelling: dict[str, str] = {}
    times: dict[str, tuple[datetime, datetime]] = {}
    actors: set[str] = set()
    for actor, at in events.values_list("actor", "at").iterator():
        actors.add(actor)
        key = actor.lower()
        spelling.setdefault(key, actor)
        first, last = times.get(key, (at, at))
        times[key] = (min(first, at), max(last, at))
    profiles = {p.login.lower(): p for p in Person.objects.filter(login__in=actors)}
    bots = {key for key, person in profiles.items() if person.is_bot}
    keys = sorted(set(times) - bots, key=lambda key: spelling[key].casefold())
    found = known(profiles[k].location for k in keys if k in profiles)
    countries: dict[str, CountryStats] = {}
    places: dict[tuple, int] = {}
    unknown, without = [], 0
    for key in keys:
        person = profiles.get(key)
        location = (person.location if person else "").strip()
        if not location:
            without += 1
            continue
        where = found.get(location)
        if where is None:
            unknown.append((spelling[key], location))
            continue
        country = countries.setdefault(where.country, CountryStats(where.country))
        country.people.append((spelling[key], location, where.city, where.region))
        first, last = times[key]
        country.first = min(country.first or first, first)
        country.last = max(country.last or last, last)
        if where.city and where.latitude is not None and where.longitude is not None:
            x, y = project(where.longitude, where.latitude)
            spot = (x, y, where.city, where.country)
            places[spot] = places.get(spot, 0) + 1
    for country in countries.values():
        languages: list[str] = []
        for region in ["", *sorted({region for *_, region in country.people if region})]:
            for language in languages_of(country.code, region):
                if language not in languages:
                    languages.append(language)
        country.languages = tuple(languages)
    ordered = sorted(countries.values(), key=lambda c: (-c.count, c.code))
    return CountryMap(
        contributors=len(keys),
        mapped=sum(c.count for c in ordered),
        without_location=without,
        unknown=unknown,
        countries=ordered,
        places=[(*spot, count) for spot, count in sorted(places.items())],
    )
