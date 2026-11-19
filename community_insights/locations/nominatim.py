"""Find the places that GeoNames does not know with Nominatim, the search of OpenStreetMap.

The usage policy of the public server (https://operations.osmfoundation.org/policies/nominatim/)
asks for at most one request per second, a name of the software in the User-Agent, and to keep
the answers: each location is asked for once (`locator.Locator`), and only by the fetch worker,
never by a page.
"""

import time

import httpx

from .found import Found
from .regions import BY_CODE

USER_AGENT = "community-insights (https://github.com/PyCalendar/community-insights)"
PAUSE = 1.0  # seconds between two requests, as the policy asks
# the kinds of answers that are a place for a dot on the map
PLACES = {
    "city",
    "town",
    "village",
    "hamlet",
    "municipality",
    "suburb",
    "borough",
    "quarter",
    "neighbourhood",
    "city_district",
    "district",
    "county",
}


class Nominatim:
    """Ask Nominatim for the place of a location, at most once a second."""

    def __init__(self, url: str, client: httpx.Client | None = None, pause: float = PAUSE):
        """The search of a Nominatim server.

        Args:
            url: The address of the server, such as ``https://nominatim.openstreetmap.org``.
            client: The HTTP client; one with the User-Agent of this software by default.
            pause: Seconds between two requests.
        """
        self.url = url.rstrip("/")
        self.client = client or httpx.Client(timeout=20, headers={"User-Agent": USER_AGENT})
        self.pause = pause
        self.last = 0.0

    def wait(self) -> None:
        """Wait until a request is allowed."""
        rest = self.last + self.pause - time.monotonic()
        if rest > 0:
            time.sleep(rest)
        self.last = time.monotonic()

    def search(self, location: str) -> Found | None:
        """Where a location is, after OpenStreetMap.

        Args:
            location: The location as written in a GitHub profile.

        Returns:
            Where it is; None if Nominatim finds nothing or cannot be reached.
        """
        self.wait()
        try:
            answer = self.client.get(
                f"{self.url}/search",
                params={
                    "q": location,
                    "format": "jsonv2",
                    "addressdetails": 1,
                    "limit": 1,
                    "accept-language": "en",
                },
            )
            answer.raise_for_status()
            results = answer.json()
        except (httpx.HTTPError, ValueError):
            return None
        if not results or not isinstance(results, list):
            return None
        return self.found(results[0])

    @staticmethod
    def found(result: dict) -> Found | None:
        """Where a result of Nominatim is.

        Args:
            result: The first result of a search, with its address.

        Returns:
            The country, the region of `regions` and, for a city or a smaller place, its name
            and coordinates; None without a country.

        Examples:
            >>> found = Nominatim.found({"lat": "51.5", "lon": "-3.2", "addresstype": "city",
            ...     "name": "Cardiff", "address": {"country_code": "gb",
            ...     "ISO3166-2-lvl4": "GB-WLS"}})
            >>> found.country, found.region, found.city, found.latitude, found.source
            ('GB', 'WLS', 'Cardiff', 51.5, 'nominatim')
        """
        address = result.get("address") or {}
        country = (address.get("country_code") or "").upper()
        if len(country) != 2:
            return None
        iso = address.get("ISO3166-2-lvl4") or address.get("ISO3166-2-lvl6") or ""
        region = iso.partition("-")[2]
        region = region if (country, region) in BY_CODE else ""
        if result.get("addresstype") not in PLACES:
            return Found(country, region, source="nominatim")
        try:
            latitude, longitude = float(result["lat"]), float(result["lon"])
        except (KeyError, TypeError, ValueError):
            return Found(country, region, source="nominatim")
        return Found(
            country, region, result.get("name") or "", latitude, longitude, source="nominatim"
        )
