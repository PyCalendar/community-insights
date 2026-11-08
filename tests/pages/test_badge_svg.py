"""The SVG of the badges: readable by screen readers and the same bytes each time."""

from community_insights.badges import badge


def test_the_badge_has_an_accessible_name():
    """Screen readers announce the label and the value once."""
    svg = badge("PR response p95", "3h").decode()
    assert 'role="img"' in svg
    assert 'aria-label="PR response p95: 3h"' in svg
    assert "<title>PR response p95: 3h</title>" in svg


def test_the_accessible_name_is_escaped():
    """Quotes and angle brackets do not break the SVG."""
    svg = badge('say "hi"', "<1d").decode()
    assert "aria-label='say \"hi\": &lt;1d'" in svg
    assert '<title>say "hi": &lt;1d</title>' in svg


def test_the_same_badge_is_the_same_bytes():
    """The mask id does not depend on how many badges were drawn before."""
    first = badge("a", "b")
    badge("other", "badge")
    assert badge("a", "b") == first
    assert b"anybadge_" not in first


def test_different_badges_have_different_mask_ids():
    """Two badges on one page do not share a mask."""
    assert (
        badge("a", "b").split(b'mask id="')[1][:19] != badge("a", "c").split(b'mask id="')[1][:19]
    )


def test_a_newer_anybadge_with_its_own_title_gives_one_title(monkeypatch):
    """anybadge 1.18 writes a role, a label and a title: the badge has each of them once.

    With both, the SVG had the attributes twice, was invalid, and the browser did not show it.
    """
    import re
    from xml.dom.minidom import parseString

    import anybadge

    drawn = anybadge.Badge.badge_svg_text.fget

    def with_own_name(self):
        """The SVG as anybadge 1.18 draws it.

        Args:
            self: The badge.

        Returns:
            The SVG with a role, a label and a title of anybadge.
        """
        return re.sub(
            r"(<svg [^>]*)>",
            r'\1 role="img" aria-label="anybadge"><title>anybadge</title>',
            drawn(self),
            count=1,
        )

    monkeypatch.setattr(anybadge.Badge, "badge_svg_text", property(with_own_name))
    svg = badge("PR response p95", "3h").decode()
    assert "anybadge" not in svg.replace("anybadge_", "")
    assert svg.count("<title>") == 1 and svg.count("aria-label=") == 1
    assert svg.count('role="img"') == 1
    parseString(svg)  # valid XML
