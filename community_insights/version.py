"""Build information of the version that runs.

Build information: written to version.json by docker/set-version.sh when the image is built; in a
checkout, default_version.json and the commit of git.
"""

import json
import subprocess
from datetime import datetime
from functools import cache
from pathlib import Path

HERE = Path(__file__).parent
VERSION_FILE = HERE / "version.json"
DEFAULT_VERSION_FILE = HERE / "default_version.json"


def git_commit() -> str:
    """The commit of the checkout, or "" without git.

    Returns:
        The full hash of the commit.
    """
    try:
        found = subprocess.run(
            ["git", "-C", str(HERE), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return found.stdout.strip()


@cache
def get() -> dict:
    """The build information, read once: version, commit, tag, time of the build."""
    path = VERSION_FILE if VERSION_FILE.exists() else DEFAULT_VERSION_FILE
    info = json.loads(path.read_text())
    if not info.get("commit_full") and not VERSION_FILE.exists():
        info["commit_full"] = git_commit()
        info["commit"] = info["commit_full"][:7]
    try:
        info["built_at"] = datetime.fromisoformat(info.get("built", ""))
    except ValueError:
        info["built_at"] = None
    return info


def source_links(source_url: str, build: dict) -> dict:
    """Where the code of this version is: the tag of a release, else the commit.

    Args:
        source_url: The address of the repository of the code.
        build: The build information: commit and tag.

    Returns:
        The address of the commit and of the code of this version.
    """
    source_url = source_url.rstrip("/")
    commit = build.get("commit_full") or ""
    links = {"commit_url": f"{source_url}/commit/{commit}" if commit else ""}
    if build.get("tag"):
        links["this_version_url"] = f"{source_url}/tree/{build['tag']}"
    elif commit:
        links["this_version_url"] = f"{source_url}/tree/{commit}"
    else:
        links["this_version_url"] = source_url
    return links
