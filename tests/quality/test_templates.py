"""Rules for the templates: JavaScript lives in static/js/, never in templates."""

import re
from pathlib import Path

import pytest

TEMPLATES = sorted((Path(__file__).parents[2] / "community_insights" / "templates").rglob("*.html"))
EVENT_HANDLER = re.compile(r"\son[a-z]+\s*=", re.IGNORECASE)
SCRIPT = re.compile(r"<script\b([^>]*)>(.*?)</script>", re.IGNORECASE | re.DOTALL)


def name(path: Path) -> str:
    """The name of a template in the test report."""
    return str(path.relative_to(path.parents[2]))


def test_there_are_templates():
    """There are templates."""
    assert len(TEMPLATES) > 20


@pytest.mark.parametrize("path", TEMPLATES, ids=name)
def test_no_event_handler_attributes(path):
    """No event handler attributes."""
    assert not EVENT_HANDLER.findall(path.read_text()), "use a data- attribute and static/js/"


@pytest.mark.parametrize("path", TEMPLATES, ids=name)
def test_no_inline_scripts(path):
    """No inline scripts."""
    for attributes, body in SCRIPT.findall(path.read_text()):
        assert "src=" in attributes, "load JavaScript from static/js/"
        assert not body.strip(), "a script with src has no body"


@pytest.mark.parametrize("path", TEMPLATES, ids=name)
def test_no_javascript_urls(path):
    """No javascript urls."""
    assert "javascript:" not in path.read_text().lower()


@pytest.mark.parametrize(
    ("html", "found"),
    [
        ('<button onclick="go()">', True),
        ('<form onsubmit="return confirm(1)">', True),
        ('<button data-confirm="Delete?">', False),
        ('<a href="/online">', False),
    ],
)
def test_the_event_handler_check(html, found):
    """The event handler check."""
    assert bool(EVENT_HANDLER.search(html)) is found
