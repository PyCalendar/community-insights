"""The countries that take part in Horizon Europe, the research programme of the EU.

Taken from the list of the European Commission, "List of participating countries in Horizon
Europe" (version of 1 January 2026), and its news of later associations. Check it when the
programme changes: SOURCE.
"""

import functools

from .places import Places

SOURCE = (
    "https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/common/"
    "guidance/list-3rd-country-participation_horizon-euratom_en.pdf"
)

MEMBER_STATES = frozenset(
    "AT BE BG CY CZ DE DK EE ES FI FR GR HR HU IE IT LT LU LV MT NL PL PT RO SE SI SK".split()
)

# Associated countries: code -> what is special about the association.
ASSOCIATED = {
    "AL": "",
    "AM": "",
    "BA": "",
    "CA": "Pillar II only",
    "CH": "since 2025",
    "EG": "being processed in the list of 1 January 2026",
    "FO": "",
    "GB": "since 2024",
    "GE": "",
    "IL": "",
    "IS": "",
    "JP": "Pillar II only, since July 2026",
    "KR": "Pillar II only, since 2025",
    "MD": "",
    "ME": "",
    "MK": "",
    "NO": "",
    "NZ": "Pillar II only",
    "RS": "",
    "TN": "",
    "TR": "",
    "UA": "",
    "XK": "",
}

HORIZON_EUROPE = MEMBER_STATES | frozenset(ASSOCIATED)


@functools.cache
def places() -> Places:
    """The names of places, read once (some MB).

    Returns:
        The places of GeoNames.
    """
    return Places()


@functools.lru_cache(maxsize=4096)
def country_of(location: str) -> str | None:
    """The country of a location as written in a GitHub profile.

    Args:
        location: The location, such as "Berlin, Germany".

    Returns:
        The two-letter code of the country, or None if it is not known.
    """
    return places().country_of(location)


def in_horizon_europe(location: str) -> bool:
    """Whether a location is in a country of Horizon Europe.

    Args:
        location: The location as written in a GitHub profile.

    Returns:
        True for the member states of the EU and the associated countries.

    Examples:
        >>> in_horizon_europe("Oslo, Norway")
        True
        >>> in_horizon_europe("San Francisco, CA")
        False
        >>> in_horizon_europe("")
        False
    """
    return country_of(location) in HORIZON_EUROPE
