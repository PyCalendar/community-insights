"""The contributors from one country, for the page Countries."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CountryStats:
    """The contributors from a country, when they contributed and which languages they speak.

    Attributes:
        code: The two-letter code of the country (ISO 3166).
        people: Each contributor: the handle, the location as written, the city or place
            found ("" for none) and the code of the region ("" for none); sorted by handle.
        first: The first contribution of anybody from the country in the time range.
        last: The last contribution of anybody from the country in the time range.
        languages: The official languages of the country, and of the regions the
            contributors name, as codes, the most spoken first.
    """

    code: str
    people: list[tuple[str, str, str, str]] = field(default_factory=list)
    first: datetime | None = None
    last: datetime | None = None
    languages: tuple[str, ...] = ()

    @property
    def count(self) -> int:
        """How many contributors are from the country.

        Examples:
            >>> CountryStats("DE", [("ann", "Berlin", "Berlin", "")]).count
            1
        """
        return len(self.people)
