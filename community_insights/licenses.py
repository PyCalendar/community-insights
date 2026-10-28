"""The licenses of the software of the site.

The licenses of the software of the site: the installed Python packages, read by pip-licenses,
the JavaScript the pages load, from static/vendor/vendor.json, and the code taken over from other
projects, from REUSE.toml.
"""

import json
import tomllib
from dataclasses import dataclass
from functools import cache
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as installed_version
from pathlib import Path

import piplicenses
from django.conf import settings
from django.templatetags.static import static
from django.urls import reverse

VENDOR = Path(__file__).parent.parent / "static" / "vendor" / "vendor.json"
REUSE = Path(__file__).parent.parent / "REUSE.toml"
PROJECT_LICENSE = "AGPL-3.0-or-later"  # the license of the project, in REUSE.toml


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


UNKNOWN = "UNKNOWN"  # what pip-licenses says for a field that is missing


def license_of(entry: dict) -> str:
    """The SPDX expression, the license field, or the license classifiers.

    Args:
        entry: A package as pip-licenses describes it.

    Returns:
        The license, "see the package" if none is given.

    Examples:
        >>> license_of({"license_expression": "MIT"})
        'MIT'
        >>> license_of({"license_expression": "UNKNOWN", "license": "BSD"})
        'BSD'
        >>> license_of({"license": "BSD " * 30, "license_classifier": ["BSD License"]})
        'BSD License'
        >>> license_of({})
        'see the package'
    """
    expression = entry.get("license_expression", UNKNOWN)
    if expression != UNKNOWN:
        return expression
    text = entry.get("license", UNKNOWN).strip()
    if text != UNKNOWN and text and "\n" not in text and len(text) < 80:
        return text
    return ", ".join(entry.get("license_classifier", [])) or "see the package"


def url_of(entry: dict) -> str:
    """The home page of a package, else its page on PyPI.

    Args:
        entry: A package as pip-licenses describes it.

    Returns:
        The address.

    Examples:
        >>> url_of({"name": "x", "home-page": "https://x.org"})
        'https://x.org'
        >>> url_of({"name": "x", "home-page": "UNKNOWN"})
        'https://pypi.org/project/x/'
    """
    url = entry.get("home-page", UNKNOWN)
    if url.startswith(("http://", "https://")):
        return url
    return f"https://pypi.org/project/{entry['name']}/"


@cache
def installed() -> dict[str, dict]:
    """The installed Python packages as pip-licenses reads them, by lower case name.

    Returns:
        The entries of pip-licenses, with the texts of their license files.
    """
    arguments = piplicenses.create_parser().parse_args(
        ["--from=mixed", "--with-system", "--with-urls", "--with-license-file", "--no-license-path"]
    )
    found: dict[str, dict] = {}
    for entry in piplicenses.get_packages(arguments):
        found.setdefault(str(entry["name"]).lower(), entry)
    return found


def license_text(name: str) -> str | None:
    """The text of the license file of an installed package.

    Args:
        name: The name of the package, in any case.

    Returns:
        The text, None if the package is not installed or ships no license file.
    """
    entry = installed().get(name.lower())
    if entry is None or entry.get("licensetext", UNKNOWN) == UNKNOWN:
        return None
    return entry["licensetext"]


@cache
def packages() -> list[Package]:
    """The installed Python packages, by name, linked to the texts of their licenses.

    Returns:
        The packages, read by pip-licenses.
    """
    found = []
    for key, entry in installed().items():
        text_url = reverse("license", args=[key]) if license_text(key) is not None else ""
        found.append(
            Package(entry["name"], entry["version"], license_of(entry), url_of(entry), text_url)
        )
    return sorted(found, key=lambda p: p.name.lower())


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

    Read from the annotations of REUSE.toml, except those of the project, under its license.
    The name is the files, the version the copyright.

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
        if annotation.get("SPDX-License-Identifier") == PROJECT_LICENSE:
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
