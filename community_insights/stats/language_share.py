"""An estimate of the languages of the contributors, for the page Languages."""

from dataclasses import dataclass, field

from ..locations.languages import languages_of, spoken_by
from .country_map import CountryMap


@dataclass
class LanguageShare:
    """The contributors who live where a language is official.

    Attributes:
        code: The code of the language in CLDR, such as ``de`` or ``cy``.
        contributors: How many contributors live in a country or region where it is official.
        countries: The code of each of these countries and how many contributors live there,
            the most first.
        speakers: How many of all contributors with a known country likely speak it: for
            each of them, the share of the people of their country who speak it (CLDR),
            whether it is official there or not.
    """

    code: str
    contributors: int = 0
    countries: list[tuple[str, int]] = field(default_factory=list)
    speakers: float = 0.0


def language_shares(found: CountryMap) -> list[LanguageShare]:
    """The languages official where the contributors live, the most contributors first.

    A contributor counts for each official language of their country, or of their region if
    it has its own (Wales: English and Welsh); a country with several official languages
    counts for each of them.

    Args:
        found: The contributors by country.

    Returns:
        The languages, by the number of contributors, then by the estimate of speakers.
    """
    shares: dict[str, LanguageShare] = {}
    by_country: dict[str, dict[str, int]] = {}
    for country in found.countries:
        for *_, region in country.people:
            for language in languages_of(country.code, region):
                share = shares.setdefault(language, LanguageShare(language))
                share.contributors += 1
                counted = by_country.setdefault(language, {})
                counted[country.code] = counted.get(country.code, 0) + 1
    for share in shares.values():
        share.countries = sorted(by_country[share.code].items(), key=lambda p: (-p[1], p[0]))
        share.speakers = sum(
            spoken_by(country.code, share.code) * country.count for country in found.countries
        )
    return sorted(shares.values(), key=lambda s: (-s.contributors, -s.speakers, s.code))
