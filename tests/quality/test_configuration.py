""".env.example and docs/reference/configuration.rst name every variable the site reads."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
SETTINGS = (ROOT / "community_insights" / "settings.py").read_text()
DOCKERFILE = (ROOT / "Dockerfile").read_text()
EXAMPLE = (ROOT / ".env.example").read_text()
REFERENCE = (ROOT / "docs" / "reference" / "configuration.rst").read_text()

# Variables of the image that are not settings of the site.
OF_THE_IMAGE = {"PYTHONUNBUFFERED", "UV_PROJECT_ENVIRONMENT", "PATH"}


def read_by_the_site() -> set[str]:
    """The variables settings.py (also its secrets), the code and the Dockerfile read.

    Returns:
        Their names, such as ``DATABASE_URL``.
    """
    names = set(re.findall(r"\b(?:env(?:\.\w+)?|kept_secret)\(\s*\"([A-Z_]+)\"", SETTINGS))
    for path in (ROOT / "community_insights").rglob("*.py"):
        names |= set(re.findall(r"os\.environ\.get\(\"([A-Z_]+)\"", path.read_text()))
    names |= set(re.findall(r"^ENV ([A-Z_]+)=", DOCKERFILE, re.MULTILINE))
    return names - OF_THE_IMAGE


VARIABLES = sorted(read_by_the_site())
IN_EXAMPLE = re.findall(r"^#? ?([A-Z_]+)=", EXAMPLE, re.MULTILINE)


def test_the_variables_are_found():
    """The search finds the variables of settings.py, the code and the Dockerfile."""
    assert {"DATABASE_URL", "SECRET_KEY", "DEFAULT_SUPERUSER", "WORKERS"} <= set(VARIABLES)


@pytest.mark.parametrize("name", VARIABLES)
def test_the_example_explains_each_variable(name):
    """Each variable is in .env.example, after a line that explains it."""
    assert name in IN_EXAMPLE, f"add {name} to .env.example"
    lines = EXAMPLE.splitlines()
    index = next(i for i, line in enumerate(lines) if re.match(rf"^#? ?{name}=", line))
    explained = next(
        line for line in reversed(lines[:index]) if not re.match(r"^#? ?[A-Z_]+=", line)
    )
    assert explained.startswith("## "), f"explain {name} in .env.example"


@pytest.mark.parametrize("name", VARIABLES)
def test_the_reference_lists_each_variable(name):
    """Each variable is in the table of docs/reference/configuration.rst."""
    assert f"``{name}``" in REFERENCE


def test_the_example_names_no_other_variable():
    """.env.example names only variables the site reads, each once."""
    assert set(IN_EXAMPLE) <= set(VARIABLES)
    assert len(IN_EXAMPLE) == len(set(IN_EXAMPLE))


def test_the_example_changes_nothing():
    """Copied to .env, the example sets nothing: every setting is a comment."""
    settings = [line for line in EXAMPLE.splitlines() if line.strip() and not line.startswith("#")]
    assert settings == []
