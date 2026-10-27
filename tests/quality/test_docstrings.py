# SPDX-FileCopyrightText: 2012-2013 Plone Foundation and the icalendar contributors
# SPDX-FileCopyrightText: 2026 Contributor Community Insights contributors
# SPDX-License-Identifier: BSD-2-Clause
"""Inspect all docstring section headings.

Adapted from icalendar (src/icalendar/tests/test_docstrings.py, BSD-2-Clause):
the headings of the Google style guide
(https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings) instead of
icalendar's, and the public classes and functions of all modules of community_insights/.

``ALLOWED_HEADINGS`` is a set of allowed headings. It may be amended as needed.
Missing sections fail the tests; icalendar reports them as expected failures (xfail), a
baseline that shrinks as the docstrings are improved.
"""

import ast
import dataclasses
import importlib
import inspect
import re
from pathlib import Path

import pytest

ALLOWED_HEADINGS = {
    "Args",
    "Attributes",
    "Returns",
    "Yields",
    "Raises",
    "Example",
    "Examples",
    "Note",
    "Notes",
    "See Also",
    "Todo",
    "Warning",
}

PACKAGE = Path(__file__).parent.parent.parent / "community_insights"
MODULES = [
    ".".join(("community_insights", *file.relative_to(PACKAGE).with_suffix("").parts)).removesuffix(
        ".__init__"
    )
    for file in PACKAGE.glob("**/*.py")
    if "migrations" not in file.parts
]


def get_public_objects():
    """The public classes and functions defined in the modules of community_insights/."""
    objs = {}
    for name in MODULES:
        module = importlib.import_module(name)
        for member_name, obj in inspect.getmembers(module):
            if member_name.startswith("_"):
                continue
            if (inspect.isclass(obj) or inspect.isfunction(obj)) and obj.__module__ == name:
                objs[f"{obj.__module__}.{obj.__qualname__}"] = obj
    return list(objs.values())


def _obj_id(obj):
    """Return the name of the object for parametrize IDs."""
    return f"{obj.__module__}.{obj.__qualname__}"


@pytest.mark.parametrize("obj", get_public_objects(), ids=_obj_id)
def test_docstring_headings_are_valid(obj):
    """Identify docstring section headings that are not one of the allowed types."""
    doc = inspect.getdoc(obj)
    if not doc:
        return
    headings = re.findall(r"^ *([A-Z][A-Za-z]+(?: [A-Za-z]+)*):(?:\n|$)", doc, re.MULTILINE)
    for heading in headings:
        assert heading in ALLOWED_HEADINGS, (
            f"Invalid docstring heading '{heading}' found in '{obj.__qualname__}'. "
            f"Allowed headings are: {', '.join(sorted(ALLOWED_HEADINGS))}"
        )


def get_all_public_methods_and_functions():
    """The public functions and the public methods of the public classes."""
    objs = []
    for obj in get_public_objects():
        if inspect.isfunction(obj):
            objs.append(obj)
        elif inspect.isclass(obj):
            for name, method in inspect.getmembers(obj, predicate=inspect.isfunction):
                if name.startswith("_") and name != "__init__":
                    continue
                if method.__module__ == obj.__module__ and method.__qualname__.startswith(
                    obj.__qualname__ + "."
                ):
                    objs.append(method)
    return objs


def _method_id(obj):
    """Return the name of the method for parametrize IDs."""
    return f"{obj.__module__}.{obj.__qualname__}"


@pytest.mark.parametrize("obj", get_all_public_methods_and_functions(), ids=_method_id)
def test_docstring_has_args_section(obj):
    """Identify docstrings that lack an Args section when the signature has parameters."""
    try:
        sig = inspect.signature(obj)
    except ValueError:
        return
    params = [p for n, p in sig.parameters.items() if n not in ("self", "cls")]
    if not params:
        return
    owner = getattr(importlib.import_module(obj.__module__), obj.__qualname__.split(".")[0], None)
    if obj.__name__ == "__init__" and dataclasses.is_dataclass(owner):
        # a dataclass makes its __init__: its fields are the Attributes of the class
        if not re.search(r"^Attributes:$", inspect.getdoc(owner) or "", re.MULTILINE):
            pytest.fail(f"'{owner.__qualname__}' lacks an Attributes section.")
        return
    doc = inspect.getdoc(obj)
    if not doc:
        return
    if not re.search(r"^Args:$", doc, re.MULTILINE):
        pytest.fail(f"'{obj.__module__}.{obj.__qualname__}' lacks an Args section.")


def check_returns_and_raises(obj):
    """Whether the source of the object returns a value and raises an exception."""
    try:
        source = inspect.cleandoc(inspect.getsource(obj))
        tree = ast.parse(source)
    except (OSError, TypeError, SyntaxError):
        return False, False
    has_returns = any(isinstance(n, ast.Return) and n.value is not None for n in ast.walk(tree))
    has_raises = any(isinstance(n, ast.Raise) for n in ast.walk(tree))
    return has_returns, has_raises


@pytest.mark.parametrize("obj", get_all_public_methods_and_functions(), ids=_method_id)
def test_docstring_has_returns_section(obj):
    """Identify docstrings of objects that return something but lack a Returns section."""
    has_ret, _ = check_returns_and_raises(obj)
    doc = inspect.getdoc(obj)
    if not has_ret or not doc:
        return
    if not re.search(r"^Returns:$", doc, re.MULTILINE):
        pytest.fail(
            f"'{obj.__module__}.{obj.__qualname__}' returns a value but lacks a Returns section."
        )


@pytest.mark.parametrize("obj", get_all_public_methods_and_functions(), ids=_method_id)
def test_docstring_has_raises_section(obj):
    """Identify docstrings of objects that raise something but lack a Raises section."""
    _, has_raise = check_returns_and_raises(obj)
    doc = inspect.getdoc(obj)
    if not has_raise or not doc:
        return
    if not re.search(r"^Raises:$", doc, re.MULTILINE):
        pytest.fail(
            f"'{obj.__module__}.{obj.__qualname__}' raises an exception but lacks a Raises section."
        )


def test_every_test_function_and_class_has_a_docstring():
    """The tests are documented, too: AGENTS.md asks for a docstring everywhere."""
    tests = Path(__file__).parent.parent
    missing = [
        f"{path.relative_to(tests)}:{node.lineno} {node.name}"
        for path in sorted(tests.rglob("*.py"))
        for node in ast.walk(ast.parse(path.read_text()))
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
        and not ast.get_docstring(node)
    ]
    assert not missing, missing
