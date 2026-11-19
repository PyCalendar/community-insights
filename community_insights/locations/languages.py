"""The official languages of countries and regions, from CLDR (Babel).

CLDR (the Unicode Common Locale Data Repository) lists the languages of each country with the
share of the people who speak them and whether they are official. A country counts for its
official languages and those that are official in fact (``de_facto_official``); a region of
`regions` counts for its own.
"""

import functools
from collections.abc import Mapping
from typing import Any

from .regions import BY_CODE

OFFICIAL = ("official", "de_facto_official")


@functools.cache
def territories() -> Mapping[str, Any]:
    """The languages of each country of CLDR, read once.

    Returns:
        By the code of the country, the languages with ``population_percent`` and
        ``official_status``.
    """
    from babel.core import get_global

    return get_global("territory_languages")


@functools.cache
def official(country: str) -> tuple[str, ...]:
    """The official languages of a country, the most spoken first.

    Args:
        country: The two-letter code, such as ``CH``.

    Returns:
        The codes of the languages, such as ``("de", "gsw", "fr", "it")``; none for a code
        that CLDR does not know.

    Examples:
        >>> official("AT"), official("ZZ")
        (('de',), ())
    """
    languages = territories().get(country, {})
    found = [
        (info.get("population_percent") or 0, code)
        for code, info in languages.items()
        if info.get("official_status") in OFFICIAL
    ]
    return tuple(code for _, code in sorted(found, key=lambda pair: (-pair[0], pair[1])))


def languages_of(country: str, region: str = "") -> tuple[str, ...]:
    """The official languages of a place: those of its region, or else of its country.

    Args:
        country: The two-letter code of the country.
        region: The code of the region in ISO 3166-2 after the country, such as ``WLS``.

    Returns:
        The codes of the languages.

    Examples:
        >>> languages_of("GB", "WLS"), languages_of("GB")
        (('en', 'cy'), ('en',))
    """
    known = BY_CODE.get((country, region))
    return known.languages if known else official(country)


def spoken_by(country: str, language: str) -> float:
    """The share of the people of a country who speak a language, after CLDR.

    Args:
        country: The two-letter code of the country.
        language: The code of the language.

    Returns:
        From 0 to 1; 0 if CLDR does not know it.

    Examples:
        >>> spoken_by("AT", "de"), spoken_by("AT", "xx")
        (0.97, 0.0)
    """
    info = territories().get(country, {}).get(language, {})
    return (info.get("population_percent") or 0) / 100
