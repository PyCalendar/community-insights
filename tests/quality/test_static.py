"""The static files: small enough for the repository, no missing source maps."""

import re
from pathlib import Path

import pytest

STATIC = Path(__file__).parents[2] / "static"
FILES = sorted(path for path in STATIC.rglob("*") if path.is_file())
# the limit of check-added-large-files in .pre-commit-config.yaml
MAX_BYTES = 500 * 1024
SOURCE_MAP = re.compile(r"sourceMappingURL=(\S+?)\s*(?:\*/)?\s*$", re.MULTILINE)


def name(path: Path) -> str:
    return str(path.relative_to(STATIC))


def test_there_are_static_files():
    assert any(path.suffix == ".css" for path in FILES)
    assert any(path.suffix == ".js" for path in FILES)


@pytest.mark.parametrize("path", FILES, ids=name)
def test_file_is_small_enough_for_the_repository(path):
    assert path.stat().st_size <= MAX_BYTES


@pytest.mark.parametrize("path", [p for p in FILES if p.suffix in (".css", ".js")], ids=name)
def test_no_source_map_that_is_missing(path):
    """A browser asks for the map of a file; it is not in the repository."""
    for source_map in SOURCE_MAP.findall(path.read_text()):
        assert (path.parent / source_map).is_file(), f"remove the sourceMappingURL of {source_map}"
