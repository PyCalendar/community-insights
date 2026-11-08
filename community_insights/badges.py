"""Flat SVG badges, drawn by anybadge with the widths of the text measured."""

import hashlib
import re
from xml.sax.saxutils import escape, quoteattr

import anybadge

# anybadge 1.18 and newer write a role, a label and a title of their own: the same attributes
# twice make the SVG invalid, so theirs are replaced by those of badge()
OWN_TITLE = re.compile(r"\s*<title>[^<]*</title>")
OWN_NAME = re.compile(r' (?:role|aria-label)="[^"]*"')


def badge(label: str, value: str, color: str = "#2a7de1") -> bytes:
    """A flat SVG badge: the label on grey, the value on the colour.

    anybadge measures the text, so long and short texts fit; the badge gets one title and
    one label for screen readers, also with the versions of anybadge that write their own. anybadge numbers its mask ids with a counter; the id is
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
    svg = OWN_TITLE.sub("", svg, count=1)
    return re.sub(
        r"<svg ([^>]*)>",
        lambda found: (
            f'<svg {OWN_NAME.sub("", found.group(1))} role="img" aria-label={quoteattr(spoken)}>'
            f"<title>{escape(spoken)}</title>"
        ),
        svg,
        count=1,
    ).encode()
