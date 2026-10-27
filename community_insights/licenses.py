"""The licenses of the software of the site.

The licenses of the software of the site: the installed Python packages, read from their metadata,
the JavaScript the pages load, from static/vendor/vendor.json, and the code taken over from other
projects, from REUSE.toml.
"""

import json
import tomllib
from dataclasses import dataclass
from functools import cache
from importlib.metadata import PackageNotFoundError, distributions
from importlib.metadata import version as installed_version
from pathlib import Path

from django.conf import settings
from django.templatetags.static import static

VENDOR = Path(__file__).parent.parent / "static" / "vendor" / "vendor.json"
REUSE = Path(__file__).parent.parent / "REUSE.toml"


@dataclass(frozen=True)
class Package:
    """Software with its version, license and where to read about it.

    Attributes:
        name: The name.
        version: The version installed or used.
        license: The license, such as an SPDX expression.
        url: Where to read about it.
        license_url: Where to read the license, "" if not known.
    """

    name: str
    version: str
    license: str
    url: str
    license_url: str = ""


def license_of(metadata) -> str:
    """The SPDX expression, the license field, or the license classifiers.

    Args:
        metadata: The metadata of an installed package.

    Returns:
        The license, "see the package" if none is given.
    """
    expression = metadata.get("License-Expression")
    if expression:
        return expression
    text = (metadata.get("License") or "").strip()
    if text and "\n" not in text and len(text) < 80:
        return text
    classifiers = [
        c.split(" :: ")[-1]
        for c in metadata.get_all("Classifier") or []
        if c.startswith("License :: ") and c.count(" :: ") > 1
    ]
    return ", ".join(classifiers) or "see the package"


def url_of(metadata) -> str:
    """The home page of a package, from its metadata, else its page on PyPI.

    Args:
        metadata: The metadata of an installed package.

    Returns:
        The address.
    """
    for entry in metadata.get_all("Project-URL") or []:
        label, _, url = entry.partition(",")
        if label.strip().lower() in ("homepage", "home", "source", "source code", "repository"):
            return url.strip()
    return metadata.get("Home-page") or f"https://pypi.org/project/{metadata['Name']}/"


@cache
def packages() -> list[Package]:
    """The installed Python packages, by name."""
    found = {}
    for distribution in distributions():
        metadata = distribution.metadata
        name = metadata["Name"]
        if not name or name.lower() in found:
            continue
        found[name.lower()] = Package(
            name, metadata["Version"] or "", license_of(metadata), url_of(metadata)
        )
    return sorted(found.values(), key=lambda p: p.name.lower())


def address(path: str) -> str:
    """The address of a link of vendor.json.

    A link of vendor.json: a web address, the license of the project, or a static file.

    Args:
        path: The link of vendor.json.

    Returns:
        The address.
    """
    if path.startswith(("http://", "https://")):
        return path
    if path == "LICENSE":
        return f"{settings.SOURCE_URL.rstrip('/')}/blob/main/LICENSE"
    return static(path)


def scripts() -> list[Package]:
    """The JavaScript and CSS the pages load, with their licenses.

    Returns:
        The projects, from static/vendor/vendor.json.
    """
    found = []
    for entry in json.loads(VENDOR.read_text()):
        version = entry.get("version", "")
        if entry.get("python_package"):
            try:
                version = installed_version(entry["python_package"])
            except PackageNotFoundError:
                version = "?"
        if entry.get("own"):
            from .version import get

            version = get()["version"]
        found.append(
            Package(
                entry["name"],
                version,
                entry["license"],
                address(entry.get("url") or settings.SOURCE_URL),
                address(entry["license_url"]),
            )
        )
    return found


def reused(path: Path = REUSE) -> list[Package]:
    """The code taken over from other projects, with its copyright and license.

    Read from the annotations of REUSE.toml, except the one of the whole project. The name is
    the files, the version the copyright.

    Args:
        path: The REUSE.toml; a missing file has no entries.

    Returns:
        The entries, linked to the files and the license texts in the repository.
    """
    if not path.is_file():
        return []
    source = settings.SOURCE_URL.rstrip("/")
    found = []
    for annotation in tomllib.loads(path.read_text()).get("annotations", []):
        paths = annotation.get("path", [])
        paths = [paths] if isinstance(paths, str) else paths
        if paths == ["**"]:
            continue  # the project itself
        copyright_ = annotation.get("SPDX-FileCopyrightText", [])
        copyright_ = [copyright_] if isinstance(copyright_, str) else copyright_
        license_ = annotation.get("SPDX-License-Identifier", "")
        found.append(
            Package(
                ", ".join(paths),
                "; ".join(copyright_),
                license_,
                f"{source}/tree/main/{paths[0].removesuffix('/**')}",
                f"{source}/blob/main/LICENSES/{license_}.txt",
            )
        )
    return found
