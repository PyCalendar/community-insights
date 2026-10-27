"""One class per module."""

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent.parent


MODULES = [
    p
    for folder in ("community_insights", "tests", "features")
    for p in (ROOT / folder).rglob("*.py")
    if "migrations" not in p.parts
]


@pytest.mark.parametrize("path", MODULES, ids=lambda p: str(p.relative_to(ROOT)))
def test_one_class_per_module(path):
    """One class per module."""
    if path.parent.name == "errors":
        return  # grouped by topic
    tree = ast.parse(path.read_text())
    classes = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name != "Meta"
    ]
    assert len(classes) <= 1, f"{path.relative_to(ROOT)} has the classes {classes}"
