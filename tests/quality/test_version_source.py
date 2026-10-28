"""The version comes from the git tag, by hatch-vcs."""

import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[2]
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text())


def test_the_version_is_dynamic():
    """pyproject.toml has no version of its own."""
    assert "version" not in PYPROJECT["project"]
    assert PYPROJECT["project"]["dynamic"] == ["version"]


def test_hatch_vcs_reads_the_version():
    """hatch-vcs builds the version, with a fallback without git."""
    assert any(r.startswith("hatch-vcs") for r in PYPROJECT["build-system"]["requires"])
    assert PYPROJECT["tool"]["hatch"]["version"]["source"] == "vcs"
    assert PYPROJECT["tool"]["hatch"]["version"]["raw-options"]["fallback_version"]


def test_the_image_gets_the_version_of_hatch_vcs():
    """docker/set-version.sh asks hatch-vcs, with the same pins as the build."""
    script = (ROOT / "docker" / "set-version.sh").read_text()
    for requirement in PYPROJECT["build-system"]["requires"]:
        assert requirement in script
