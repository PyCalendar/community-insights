"""The colours have enough contrast in both themes."""

import re
from pathlib import Path

import pytest

CSS = (Path(__file__).parent.parent.parent / "static" / "style.css").read_text()


AA = 4.5  # WCAG AA for normal text


def block(selector: str) -> dict[str, str]:
    """The custom properties of the first rule with the selector."""
    start = CSS.index(selector + " {")
    body = CSS[start : CSS.index("}", start)]
    return dict(re.findall(r"(--[a-z-]+):\s*(#[0-9a-fA-F]{6})", body))


LIGHT = block(":root")


DARK = {**LIGHT, **block(':root[data-theme="dark"]')}


def luminance(color: str) -> float:
    def channel(value: int) -> float:
        c = value / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (int(color[i : i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(a: str, b: str) -> float:
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


PAIRS = [
    ("--text", "--surface"),
    ("--text", "--surface-tint"),
    ("--text-muted", "--surface"),
    ("--text-muted", "--surface-tint"),
    ("--link", "--surface"),
    ("--link", "--surface-tint"),
    ("--link-hover", "--surface"),
    ("--nav-text", "--nav-bg"),
    ("--button-text", "--button-bg"),
    ("--button-text", "--button-hover-bg"),
    ("--danger-text", "--surface"),
]


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize(("text", "background"), PAIRS)
def test_contrast(theme, text, background):
    colors = LIGHT if theme == "light" else DARK
    ratio = contrast(colors[text], colors[background])
    assert ratio >= AA, f"{theme}: {text} on {background} is {ratio:.2f}"


def test_the_dark_theme_is_the_same_for_the_switch_and_the_system():
    media = CSS[CSS.index("@media (prefers-color-scheme: dark)") :]
    system = dict(re.findall(r"(--[a-z-]+):\s*(#[0-9a-fA-F]{6})", media[: media.index("}")]))
    assert system == block(':root[data-theme="dark"]')


def test_chart_text_contrast():
    from community_insights import charts

    assert contrast(charts.INK["light"], LIGHT["--surface"]) >= AA
    assert contrast(charts.INK["dark"], DARK["--surface"]) >= AA
