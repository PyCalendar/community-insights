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
