"""Flat SVG badges."""

from xml.sax.saxutils import escape

CHAR_WIDTH = 6.6
PAD = 10


def width(text: str) -> int:
    """The width of a part of a badge with the text, in pixels.

    Args:
        text: The text.

    Returns:
        The width.
    """
    return round(len(text) * CHAR_WIDTH + 2 * PAD)


def badge(label: str, value: str, color: str = "#2a7de1") -> bytes:
    """A flat SVG badge: the label on grey, the value on the colour.

    Args:
        label: The text of the left side.
        value: The text of the right side.
        color: The colour of the right side.

    Returns:
        The SVG.
    """
    left, right = width(label), width(value)
    total = left + right
    label, value = escape(label), escape(value)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total}" height="20" role="img" aria-label="{label}: {value}">
<title>{label}: {value}</title>
<clipPath id="r"><rect width="{total}" height="20" rx="3"/></clipPath>
<g clip-path="url(#r)"><rect width="{left}" height="20" fill="#555"/><rect x="{left}" width="{right}" height="20" fill="{color}"/></g>
<g fill="#fff" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11" text-anchor="middle">
<text x="{left / 2}" y="14">{label}</text><text x="{left + right / 2}" y="14">{value}</text></g>
</svg>""".encode()
