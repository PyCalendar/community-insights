"""Flat SVG badges, drawn by anybadge with the widths of the text measured."""

import hashlib
import re
from xml.sax.saxutils import escape, quoteattr

import anybadge


def badge(label: str, value: str, color: str = "#2a7de1") -> bytes:
    """A flat SVG badge: the label on grey, the value on the colour.

    anybadge measures the text, so long and short texts fit; the badge gets a title and a
    label for screen readers. anybadge numbers its mask ids with a counter; the id is
    derived from the texts instead, so the same badge is always the same bytes.

    Args:
        label: The text of the left side.
        value: The text of the right side.
        color: The colour of the right side.

    Returns:
        The SVG.

    Examples:
        >>> svg = badge("PR response p95", "3h <1d").decode()
        >>> "<title>PR response p95: 3h &lt;1d</title>" in svg and 'role="img"' in svg
        True
        >>> badge("a", "b") == badge("a", "b")
        True
    """
    drawn = anybadge.Badge(label, value, default_color=color)
    spoken = f"{label}: {value}"
    stable = "badge-" + hashlib.sha256(f"{spoken}\n{color}".encode()).hexdigest()[:12]
    svg = drawn.badge_svg_text.replace(f'"{drawn.mask_str}"', f'"{stable}"').replace(
        f"#{drawn.mask_str})", f"#{stable})"
    )
    return re.sub(
        r"<svg ([^>]*)>",
        lambda found: (
            f'<svg {found.group(1)} role="img" aria-label={quoteattr(spoken)}>'
            f"<title>{escape(spoken)}</title>"
        ),
        svg,
        count=1,
    ).encode()
