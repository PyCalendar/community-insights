import re
from urllib.parse import parse_qsl, urlencode, urlsplit

from django import template
from django.urls import Resolver404, resolve, reverse
from django.utils.html import format_html
from django.utils.translation import gettext as _

from .. import errors, locations
from ..stats import format_duration

register = template.Library()


@register.filter
def error_help(code: str):
    """A link to the description of a stored error code, or nothing.

    Args:
        code: The name of an error class, as stored with a fetch or a token.

    Returns:
        The link *What to do*, "" for an unknown code.
    """
    cls = errors.by_code(code)
    if cls is None:
        return ""
    return format_html('<a href="{}" title="{}">{}</a>', cls.docs_url(), cls.title, _("What to do"))


@register.filter
def get(mapping, key):
    """The value of a key of a dictionary in a template.

    Args:
        mapping: A dictionary, or anything else.
        key: The key.

    Returns:
        The value, None if there is none.
    """
    return mapping.get(key) if hasattr(mapping, "get") else None


@register.filter(name="zip")
def zip_lists(a, b):
    """Two lists side by side in a template.

    Args:
        a: The first list.
        b: The second list.

    Returns:
        The pairs, as long as the shorter list.
    """
    return zip(a, b, strict=False)


@register.filter
def number(value):
    """A number of a table: "-" for none, whole numbers without a point.

    Args:
        value: A number, None or infinite.

    Returns:
        The number to show.
    """
    if value is None or value == float("inf"):
        return "-"
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


@register.filter
def split(text):
    """The words of a text in a template.

    Args:
        text: The text.

    Returns:
        The words.
    """
    return text.split()


@register.filter
def duration(seconds):
    """Seconds as a duration, such as 3h 12min.

    Args:
        seconds: The seconds.

    Returns:
        The duration in two units at most.
    """
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


@register.simple_tag
def share_formats() -> list[tuple[str, str]]:
    """The formats to share an image in: the name of static/js/share.js and a title.

    Returns:
        Pairs of the name and the title, Markdown first.
    """
    return [
        ("markdown", "Markdown"),
        ("rst", "reStructuredText"),
        ("html", "HTML"),
        ("link", _("Link")),
    ]


@register.simple_tag(takes_context=True)
def chart_share_url(context, src: str) -> str:
    """The address of the page to share a chart, coming from the page shown.

    Args:
        context: The context of the template, with the request.
        src: The address of the chart, with its parameters.

    Returns:
        The address of the share page, "" if src is no chart.
    """
    parts = urlsplit(src)
    try:
        match = resolve(parts.path)
    except Resolver404:
        return ""
    if match.url_name != "chart":
        return ""
    parameters = [(k, v) for k, v in parse_qsl(parts.query) if k not in ("theme", "from")]
    request = context.get("request")
    if request is not None:
        parameters.append(("from", request.get_full_path()))
    return reverse("chart_share", kwargs=match.kwargs) + "?" + urlencode(parameters)


@register.filter
def fraction_total(person, column: str):
    """The total a column is a part of, such as the pull requests opened for those merged.

    Args:
        person: A contributor, or the sums of a group (a dictionary).
        column: The name of a variable.

    Returns:
        The total, None for a column that is no part of another one.

    Examples:
        >>> fraction_total({"prs_total": 5, "prs_merged": 3}, "prs_merged")
        5
        >>> fraction_total({"prs_total": 5}, "prs_reviewed") is None
        True
    """
    from ..query import FRACTIONS

    total = FRACTIONS.get(column)
    if total is None:
        return None
    if isinstance(person, dict):
        return number(person.get(total))
    return getattr(person, total, None)


@register.filter
def anchor(name: str) -> str:
    """The anchor of a heading in the documentation, as Sphinx makes it.

    Args:
        name: The text of the heading, such as ``prs_merged``.

    Returns:
        The anchor, such as ``prs-merged``.

    Examples:
        >>> anchor("prs_merged")
        'prs-merged'
    """
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
