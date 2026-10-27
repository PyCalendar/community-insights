"""The country of a location as people write it in their GitHub profile."""

import re
import unicodedata

import geonamescache

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
    its two-letter code), a state of the US or a city; a city with a name that many cities have
    is the one with the most people.

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
        self.cities: dict[str, tuple[int, str]] = {}
        for city in cache.get_cities().values():
            names = {city["name"], *(n for n in city["alternatenames"] if n.isascii())}
            for name in names:
                key = plain(name)
                known = self.cities.get(key)
                if known is None or known[0] < city["population"]:
                    self.cities[key] = (city["population"], city["countrycode"])

    def country_of(self, location: str) -> str | None:
        """The country of a location.

        Args:
            location: The location as written in a GitHub profile.

        Returns:
            The two-letter code of the country (ISO 3166), or None if no part is known.
        """
        parts = [p for p in SEPARATORS.split(location or "") if p.strip()]
        for index in reversed(range(len(parts))):
            found = self.part_country(parts[index], after_city=index > 0)
            if found:
                return found
        return None

    def part_country(self, part: str, after_city: bool) -> str | None:
        """The country of one part of a location.

        Args:
            part: A part between commas, such as "Germany", "DE", "CA" or "Berlin".
            after_city: Whether other parts are before it: then "CA" is California.

        Returns:
            The two-letter code of the country, or None.
        """
        text = part.strip()
        if len(text) == 2 and text.isupper():
            if after_city and text in self.state_codes:
                return "US"
            if text in self.codes:
                return text
        key = plain(text)
        return self.countries.get(key) or self.states.get(key) or self.city_country(key)

    def city_country(self, key: str) -> str | None:
        """The country of the biggest city of that name.

        Args:
            key: The name of a city, as given by `plain`.

        Returns:
            The two-letter code of the country, or None.
        """
        found = self.cities.get(key)
        return found[1] if found else None
