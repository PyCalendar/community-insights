"""The links to the documentation of this project lead to its latest version."""

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
DOCS = re.compile(r"https://community-insights\.readthedocs\.io(/[^\s\"'<>)`]*)?")


def tracked_text_files() -> list[Path]:
    """The files git knows of, without the prompts and the binary ones."""
    names = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    files = []
    for name in names:
        path = ROOT / name
        if name.startswith(".prompts/") or not path.is_file():
            continue
        try:
            path.read_text()
        except UnicodeDecodeError:
            continue
        files.append(path)
    return files


FILES = tracked_text_files()


def test_the_files_link_to_the_docs():
    assert any(DOCS.search(path.read_text()) for path in FILES)


@pytest.mark.parametrize("path", FILES, ids=lambda path: str(path.relative_to(ROOT)))
def test_links_lead_to_the_latest_version(path):
    for match in DOCS.finditer(path.read_text()):
        assert (match.group(1) or "").startswith("/en/latest/"), match.group(0)
