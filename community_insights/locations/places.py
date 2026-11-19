"""The country of a location as people write it in their GitHub profile."""

import re
import unicodedata

import geonamescache

from .found import Found
from .regions import BY_GEONAMES, BY_NAME

# Names people write that are not the names of the countries in GeoNames.
ALIASES = {
    "usa": "US",
    "u.s.a.": "US",
    "u.s.": "US",
    "united states of america": "US",
    "america": "US",
    "uk": "GB",
    "u.k.": "GB",
    "great britain": "GB",
    "britain": "GB",
    "england": "GB",
    "scotland": "GB",
    "wales": "GB",
    "northern ireland": "GB",
    "deutschland": "DE",
    "osterreich": "AT",
    "schweiz": "CH",
    "suisse": "CH",
    "svizzera": "CH",
    "espana": "ES",
    "italia": "IT",
    "nederland": "NL",
    "the netherlands": "NL",
    "holland": "NL",
    "belgie": "BE",
    "belgique": "BE",
    "sverige": "SE",
    "norge": "NO",
    "danmark": "DK",
    "suomi": "FI",
    "polska": "PL",
    "cesko": "CZ",
    "czechia": "CZ",
    "czech republic": "CZ",
    "magyarorszag": "HU",
    "hellas": "GR",
    "turkey": "TR",
    "turkiye": "TR",
    "brasil": "BR",
    "russia": "RU",
    "korea": "KR",
    "south korea": "KR",
    "republic of korea": "KR",
    "vietnam": "VN",
    "uae": "AE",
}
SEPARATORS = re.compile(r"\s*(?:[,;/|·()]|\s-\s|\s+and\s+)\s*")
SMALLEST_CITY = 15000  # people: the cities GeoNames lists in geonamescache


def plain(text: str) -> str:
    """Text to compare names: lower case, without accents and spaces around.

    Args:
        text: A name as written.

    Returns:
        The name in lower case without accents.

    Examples:
        >>> plain(" Zürich ")
        'zurich'
    """
    decomposed = unicodedata.normalize("NFKD", text.strip().casefold())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


class Places:
    """Countries, US states and cities by name, to find the country of a location.

    The location is split at commas and similar; the parts are tried from the last to the
    first, because people write "Berlin, Germany". A part is a country (its name, an alias or
    its two-letter code), a region with languages of its own (`regions`), a state of the US or
    a city; a city with a name that many cities have is the one with the most people, in the
    country named if there is one.

    Examples:
        >>> places = Places()
        >>> places.country_of("Berlin, Germany")
        'DE'
        >>> places.country_of("Lyon")
        'FR'
        >>> places.country_of("Portland, OR")
        'US'
        >>> places.country_of("the internet") is None
        True
    """

    def __init__(self):
        """Read the names of GeoNames (geonamescache)."""
        cache = geonamescache.GeonamesCache(min_city_population=SMALLEST_CITY)
        self.countries = {plain(c["name"]): code for code, c in cache.get_countries().items()}
        self.countries.update(ALIASES)
        self.codes = set(cache.get_countries())
        self.states = {plain(s["name"]): "US" for s in cache.get_us_states().values()}
        self.state_codes = set(cache.get_us_states())
        # by name: the cities of that name, the biggest first; each a tuple of
        # (population, country, GeoNames region, latitude, longitude, name)
        self.cities: dict[str, list[tuple]] = {}
        for city in cache.get_cities().values():
            names = {city["name"], *(n for n in city["alternatenames"] if n.isascii())}
            row = (
                city["population"],
                city["countrycode"],
                city["admin1code"],
                city["latitude"],
                city["longitude"],
                city["name"],
            )
            for name in names:
                self.cities.setdefault(plain(name), []).append(row)
        for rows in self.cities.values():
            rows.sort(key=lambda row: -row[0])

    def country_of(self, location: str) -> str | None:
        """The country of a location.

        Args:
            location: The location as written in a GitHub profile.

        Returns:
            The two-letter code of the country (ISO 3166), or None if no part is known.
        """
        found = self.find(location)
        return found.country if found else None

    def find(self, location: str) -> Found | None:
        """The country of a location, and its region and city if they are named.

        Args:
            location: The location as written in a GitHub profile.

        Returns:
            Where it is, or None if no part is known.

        Examples:
            >>> found = Places().find("Cardiff, Wales")
            >>> found.country, found.region, found.city, round(found.latitude)
            ('GB', 'WLS', 'Cardiff', 51)
            >>> Places().find("Germany").city
            ''
        """
        parts = [p.strip() for p in SEPARATORS.split(location or "") if p.strip()]
        country, region, city = None, None, None
        for index in reversed(range(len(parts))):
            key = plain(parts[index])
            named = BY_NAME.get(key)
            if named and country in (None, named.country):
                country, region = named.country, region or named
                continue
            code = self.part_country(parts[index], after_city=index > 0)
            if code:
                country = country or code
                continue
            if city is None:
                city = next(
                    (row for row in self.cities.get(key, ()) if country in (None, row[1])), None
                )
                country = country or (city[1] if city else None)
        if country is None:
            return None
        if city is not None and city[1] != country:
            city = None
        if region is None and city is not None:
            region = BY_GEONAMES.get((country, city[2]))
        if city is None:
            return Found(country, region.code if region else "")
        return Found(country, region.code if region else "", city[5], city[3], city[4])

    def part_country(self, part: str, after_city: bool) -> str | None:
        """The country of one part of a location that names a country or a state of the US.

        Args:
            part: A part between commas, such as "Germany", "DE", "CA" or "Texas".
            after_city: Whether other parts are before it: then "CA" is California.

        Returns:
            The two-letter code of the country, or None; cities are not looked at.
        """
        text = part.strip()
        if len(text) == 2 and text.isupper():
            if after_city and text in self.state_codes:
                return "US"
            if text in self.codes:
                return text
        key = plain(text)
        return self.countries.get(key) or self.states.get(key)
