"""Find the places of the locations of people once, and keep them in the database."""

from django.conf import settings

from ..models import Location
from .found import Found
from .horizon import places
from .nominatim import Nominatim
from .places import SEPARATORS, plain
from .regions import BY_NAME


def only_country(text: str) -> bool:
    """Whether a location names nothing but countries, regions or states of the US.

    Args:
        text: The location.

    Returns:
        True for "Germany", "Wales" or "Texas, USA"; False for "Ulm, Germany".

    Examples:
        >>> only_country("Wales, UK"), only_country("Ulm, Germany")
        (True, False)
    """
    parts = [p for p in SEPARATORS.split(text) if p.strip()]
    return all(
        plain(part) in BY_NAME or places().part_country(part, after_city=index > 0)
        for index, part in enumerate(parts)
    )


def as_found(row: Location) -> Found | None:
    """What a row of the database says.

    Args:
        row: The location kept.

    Returns:
        Where it is; None if it was not found.
    """
    if not row.country:
        return None
    return Found(row.country, row.region, row.city, row.latitude, row.longitude, row.source)


class Locator:
    """Where the locations of people are: from the database, else found and kept.

    GeoNames is asked first (offline). Nominatim is asked when GeoNames finds no country, or
    finds the country but not the place of a location that names more than the country.
    """

    def __init__(self, nominatim: Nominatim | None = None, most: int | None = None):
        """A locator.

        Args:
            nominatim: The search of OpenStreetMap; None for GeoNames only.
            most: How many locations Nominatim may be asked for; None for
                ``NOMINATIM_PER_FETCH``. The others are kept as GeoNames found them, and
                asked for when GeoNames knows nothing, in the next fetch.
        """
        self.nominatim = nominatim
        self.left = settings.NOMINATIM_PER_FETCH if most is None else most

    @classmethod
    def from_settings(cls) -> "Locator":
        """The locator of the settings: with Nominatim if ``NOMINATIM_URL`` is set.

        Returns:
            The locator.
        """
        url = settings.NOMINATIM_URL
        return cls(Nominatim(url) if url else None)

    def offline(self, text: str) -> Found | None:
        """Where a location is after GeoNames.

        Args:
            text: The location.

        Returns:
            Where it is, or None.
        """
        return places().find(text)

    def wants_more(self, text: str, found: Found | None) -> bool:
        """Whether to ask Nominatim: GeoNames found nothing, or no place of a longer text.

        Args:
            text: The location.
            found: What GeoNames found.

        Returns:
            Whether to ask.

        Examples:
            >>> locator = Locator()
            >>> locator.wants_more("Germany", Found("DE"))
            False
            >>> locator.wants_more("Ulm, DE", Found("DE"))
            True
            >>> locator.wants_more("Wales", Found("GB", "WLS")), locator.wants_more("x", None)
            (False, True)
        """
        if found is None:
            return True
        return not found.city and not only_country(text)

    def locate(self, texts) -> dict[str, Found | None]:
        """Where each location is: kept ones from the database, new ones found and kept.

        Args:
            texts: The locations, as written; empty ones are left out.

        Returns:
            By location, where it is, or None if it is not known.
        """
        wanted = {text.strip() for text in texts if text and text.strip()}
        kept = {row.text: row for row in Location.objects.filter(text__in=wanted)}
        result = {text: as_found(row) for text, row in kept.items()}
        for text in sorted(wanted - kept.keys()):
            found = self.offline(text)
            if self.nominatim and self.left > 0 and self.wants_more(text, found):
                self.left -= 1
                better = self.nominatim.search(text)
                if better and (found is None or better.country == found.country):
                    found = better
            Location.objects.update_or_create(
                text=text,
                defaults={
                    "country": found.country if found else "",
                    "region": found.region if found else "",
                    "city": found.city if found else "",
                    "latitude": found.latitude if found else None,
                    "longitude": found.longitude if found else None,
                    "source": found.source if found else "",
                },
            )
            result[text] = found
        return result


def known(texts) -> dict[str, Found | None]:
    """Where locations are, for a page: kept ones from the database, others after GeoNames.

    A page never asks Nominatim and writes nothing; the fetch keeps the places.

    Args:
        texts: The locations.

    Returns:
        By location, where it is, or None.
    """
    wanted = {text.strip() for text in texts if text and text.strip()}
    kept = {row.text: as_found(row) for row in Location.objects.filter(text__in=wanted)}
    return kept | {text: places().find(text) for text in wanted - kept.keys()}
