"""A part of a country with languages of its own, such as Wales."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Region:
    """A region whose official languages differ from those of its country.

    Attributes:
        country: The two-letter code of the country, such as ``GB``.
        code: The code of the region in ISO 3166-2 after the country, such as ``WLS``.
        geonames: The code of the region in GeoNames (``admin1code`` of its cities).
        names: The names people write, as compared (`places.plain`).
        languages: The official languages of the region, as codes of CLDR, the most
            spoken first.
    """

    country: str
    code: str
    geonames: str
    names: tuple[str, ...]
    languages: tuple[str, ...]
