"""Where a location of a GitHub profile is: its country, region and place."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Found:
    """The country of a location, and its region and place if they are clear.

    Attributes:
        country: The two-letter code of the country (ISO 3166).
        region: The code of a region of `regions` in ISO 3166-2 after the country, such as
            ``WLS``; "" for none.
        city: The name of the city or place, "" if the location names only a country or a
            region.
        latitude: Degrees north of the place, None without a place.
        longitude: Degrees east of the place, None without a place.
        source: Who found it: ``geonames`` (offline) or ``nominatim`` (OpenStreetMap).
    """

    country: str
    region: str = ""
    city: str = ""
    latitude: float | None = None
    longitude: float | None = None
    source: str = "geonames"
