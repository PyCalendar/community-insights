# SPDX-FileCopyrightText: 2012-2013 Plone Foundation and the icalendar contributors
# SPDX-FileCopyrightText: 2026 Contributor Community Insights contributors
# SPDX-License-Identifier: BSD-2-Clause
"""This file tests the source code provided by the documentation.

Adapted from icalendar (src/icalendar/tests/test_with_doctest.py, BSD-2-Clause):
the modules of community_insights/ and the documents of docs/ instead of icalendar's.

See
- doctest documentation: https://docs.python.org/3/library/doctest.html

This file should be tested, too:

    >>> print("Hello World!")
    Hello World!

"""

import doctest
import importlib
from pathlib import Path

import pytest

HERE = Path(__file__).absolute().parent
REPOSITORY = HERE.parent.parent
PACKAGE = REPOSITORY / "community_insights"

PYTHON_FILES = [
    file for file in PACKAGE.glob("**/*.py") if "migrations" not in file.relative_to(PACKAGE).parts
]

MODULE_NAMES = [
    ".".join(
        ("community_insights", *python_file.relative_to(PACKAGE).with_suffix("").parts)
    ).removesuffix(".__init__")
    for python_file in PYTHON_FILES
] + ["tests.quality.test_with_doctest"]

DOCUMENT_PATHS = list(REPOSITORY.glob("docs/**/*.rst"))


def test_this_module_is_among_them() -> None:
    """The examples of this file run, too."""
    assert __name__ in MODULE_NAMES


@pytest.mark.parametrize("filename", ["index.rst", "tutorial.rst"])
def test_files_is_included(filename: str) -> None:
    """The documents are found."""
    assert any(path.name == filename for path in DOCUMENT_PATHS)


@pytest.mark.parametrize("module_name", MODULE_NAMES)
def test_docstring_of_python_file(module_name: str) -> None:
    """This test runs doctest on the Python module."""
    module = importlib.import_module(module_name)
    test_result = doctest.testmod(module, name=module_name)
    assert test_result.failed == 0, f"{test_result.failed} errors in {module_name}"


@pytest.mark.parametrize("document", DOCUMENT_PATHS, ids=lambda p: p.name)
def test_documentation_file(document: Path) -> None:
    """This test runs doctest on a documentation file."""
    test_result = doctest.testfile(str(document), module_relative=False, raise_on_error=False)
    assert test_result.failed == 0, f"{test_result.failed} errors in {document.name}"
