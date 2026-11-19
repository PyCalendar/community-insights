"""The names of countries and languages in the language of the page, from CLDR (Babel)."""

import functools

from django.utils import translation


@functools.lru_cache(maxsize=32)
def locale(language: str):
    """The locale of Babel of a language of Django, English if Babel does not know it.

    Args:
        language: The language of Django, such as ``de`` or ``pt-br``.

    Returns:
        The locale.
    """
    from babel import Locale, UnknownLocaleError

    try:
        return Locale.parse(translation.to_locale(language or "en"))
    except (UnknownLocaleError, ValueError):
        return Locale.parse("en")


def country_name(code: str, language: str | None = None) -> str:
    """The name of a country.

    Args:
        code: The two-letter code, such as ``DE``.
        language: The language of the name; the active one by default.

    Returns:
        The name; CLDR calls a code it does not know "Unknown Region".

    Examples:
        >>> country_name("DE", "de"), country_name("GB", "en"), country_name("XK", "en")
        ('Deutschland', 'United Kingdom', 'Kosovo')
    """
    names = locale(language or translation.get_language()).territories
    return names.get(code) or locale("en").territories.get(code) or code


def language_name(code: str, language: str | None = None) -> str:
    """The name of a language.

    Args:
        code: The code in CLDR, such as ``cy``.
        language: The language of the name; the active one by default.

    Returns:
        The name, or the code if CLDR does not know it.

    Examples:
        >>> language_name("cy", "en"), language_name("de", "de")
        ('Welsh', 'Deutsch')
    """
    names = locale(language or translation.get_language()).languages
    return names.get(code) or locale("en").languages.get(code) or code
