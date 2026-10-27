from django import template
from django.utils.html import format_html

from .. import errors, locations
from ..stats import format_duration

register = template.Library()


@register.filter
def error_help(code: str):
    """A link to the description of a stored error code, or nothing."""
    cls = errors.by_code(code)
    if cls is None:
        return ""
    return format_html('<a href="{}" title="{}">What to do</a>', cls.docs_url(), cls.title)


@register.filter
def get(mapping, key):
    """The value of a key of a dictionary in a template."""
    return mapping.get(key) if hasattr(mapping, "get") else None


@register.filter(name="zip")
def zip_lists(a, b):
    """Two lists side by side in a template."""
    return zip(a, b, strict=False)


@register.filter
def number(value):
    """A number of a table: "-" for none, whole numbers without a point."""
    if value is None or value == float("inf"):
        return "-"
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


@register.filter
def split(text):
    """The words of a text in a template."""
    return text.split()


@register.filter
def duration(seconds):
    """Seconds as a duration, such as 3h 12min."""
    return format_duration(seconds)


@register.filter
def horizon_europe(location: str) -> bool:
    """Whether a location is in a country of Horizon Europe.

    Args:
        location: The location of a GitHub profile.

    Returns:
        True for the countries of Horizon Europe.
    """
    return locations.in_horizon_europe(location or "")


@register.filter
def country(location: str) -> str:
    """The country code of a location, "" if it is not known.

    Args:
        location: The location of a GitHub profile.

    Returns:
        The two-letter code of the country.
    """
    return locations.country_of(location or "") or ""
