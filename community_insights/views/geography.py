"""The pages Countries and Languages: where the contributors are from and what they speak."""

import json
import math

from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from .. import stats
from ..locations.names import country_name, language_name, locale
from .scope import scope_of, scope_view, stats_page

LEVELS = 5  # the shades of the heat map, from few to most contributors


def heat(count: int, most: int) -> int:
    """The shade of a country on the map: 0 for none, 1 for few to ``LEVELS`` for the most.

    The shades follow the logarithm, so one country with many contributors does not leave
    all others in the lightest shade.

    Args:
        count: The contributors from the country.
        most: The contributors from the country with the most.

    Returns:
        The shade.

    Examples:
        >>> heat(0, 10), heat(1, 10), heat(3, 10), heat(10, 10), heat(1, 1)
        (0, 1, 2, 5, 5)
    """
    if count <= 0:
        return 0
    if most <= 1:
        return LEVELS
    return 1 + min(LEVELS - 1, math.floor((LEVELS - 1) * math.log(count) / math.log(most)))


def tip(count: int, name: str) -> str:
    """The tool tip of a country on the map.

    Args:
        count: The contributors from the country.
        name: The name of the country.

    Returns:
        Such as "3 contributors from Germany".
    """
    return ngettext(
        "%(count)s contributor from %(country)s",
        "%(count)s contributors from %(country)s",
        count,
    ) % {"count": count, "country": name}


def map_names() -> dict[str, str]:
    """The names of all countries, by code, for the tool tips of countries without anybody.

    Returns:
        The names in the language of the page.
    """
    return {
        code: name
        for code, name in locale_names().items()
        if len(code) == 2 and code.isalpha() and code.isupper()
    }


def locale_names() -> dict[str, str]:
    """The names of the territories of CLDR in the language of the page.

    Returns:
        By code, the name.
    """
    from django.utils import translation

    return dict(locale(translation.get_language() or "en").territories)


@scope_view
def countries(request, scope):
    """Where the contributors are from: a map of the world and the numbers of each country.

    Args:
        request: The request.
        scope: The text of the scope.

    Returns:
        The page.
    """
    scope = scope_of(request, scope)
    found = stats.country_map(scope.repositories, scope.since, scope.until)
    most = found.countries[0].count if found.countries else 0
    rows = []
    for country in found.countries:
        name = country_name(country.code)
        rows.append(
            {
                "stats": country,
                "name": name,
                "heat": heat(country.count, most),
                "tip": tip(country.count, name),
                "languages": [language_name(code) for code in country.languages],
            }
        )
    places = [
        [
            x,
            y,
            ngettext(
                "%(place)s: %(count)s contributor",
                "%(place)s: %(count)s contributors",
                count,
            )
            % {"place": f"{city}, {country_name(code)}", "count": count},
        ]
        for x, y, city, code, count in found.places
    ]
    return stats_page(
        request,
        scope,
        "community/countries.html",
        {
            "scope": scope,
            "found": found,
            "rows": rows,
            "places_json": json.dumps(places, ensure_ascii=False),
            "names_json": json.dumps(map_names(), ensure_ascii=False, sort_keys=True),
            # the tip of a country without contributors; the script puts in the name
            "nobody": _("No contributors from %(country)s") % {"country": "{country}"},
        },
    )


@scope_view
def languages(request, scope):
    """An estimate of the languages of the contributors, from the countries they are from.

    Args:
        request: The request.
        scope: The text of the scope.

    Returns:
        The page.
    """
    scope = scope_of(request, scope)
    found = stats.country_map(scope.repositories, scope.since, scope.until)
    rows = [
        {
            "share": share,
            "name": language_name(share.code),
            "percent": 100 * share.contributors / found.mapped if found.mapped else 0,
            "countries": [(code, country_name(code), count) for code, count in share.countries],
        }
        for share in stats.language_shares(found)
    ]
    return stats_page(
        request,
        scope,
        "community/languages.html",
        {"scope": scope, "found": found, "rows": rows},
    )
