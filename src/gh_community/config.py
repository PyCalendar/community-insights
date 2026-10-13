"""Loading and creating the YAML configuration."""

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

PACKAGE_NAME = "gh-community"


TOKEN_ACCESS = """\
The token only needs read access:
  - public repositories: no scopes (a token just raises the rate limit)
  - private repositories, classic token: the 'repo' scope
  - private repositories, fine-grained token: select the repositories, with
    read-only 'Pull requests' (Metadata read-only is added automatically)
  - GitHub Actions: GITHUB_TOKEN with 'pull-requests: read' and 'contents: read'
"""


def user_config_path() -> Path:
    """$XDG_CONFIG_HOME (default ~/.config) / package name / config.yaml."""
    base = os.environ.get("XDG_CONFIG_HOME")
    base_dir = (
        Path(base) if base and Path(base).is_absolute() else Path.home() / ".config"
    )
    return base_dir / PACKAGE_NAME / "config.yaml"


@dataclass
class Config:
    token: str
    repositories: list[str]


def _read(path: Path | None) -> dict:
    """Read the file at path, or the first default one; {} if there is none."""
    if path is None:
        path = next(
            (p for p in (Path("config.yaml"), user_config_path()) if p.is_file()), None
        )
        if path is None:
            return {}
    return yaml.safe_load(Path(path).read_text()) or {}


def resolve_repository(name: str, known: list[str]) -> str:
    """Expand a short repository name to owner/name using the known repositories.

    The long form is returned unchanged. A short form must match exactly one
    known repository, otherwise it is not clearly identified: ValueError.
    """
    if "/" in name:
        owner, _, repo = name.partition("/")
        if not owner or not repo or "/" in repo or " " in name:
            raise ValueError(f"{name!r} is not of the form owner/name.")
        return name
    matches = [k for k in known if k.partition("/")[2].lower() == name.lower()]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise ValueError(
            f"{name!r} is not a known repository, use the form owner/name."
        )
    raise ValueError(f"{name!r} is ambiguous: {', '.join(matches)}.")


def load_config(
    path: Path | None = None,
    token: str | None = None,
    repositories: list[str] | None = None,
) -> Config:
    """Combine the arguments with the configuration file.

    Arguments override the file. The token is taken from the argument, then
    $GITHUB_TOKEN (as set by GitHub Actions), then the file. The file is
    optional if the arguments are enough.
    """
    if path is not None and not Path(path).is_file():
        raise SystemExit(f"Configuration file not found: {path}")
    data = _read(path)
    token = token or os.environ.get("GITHUB_TOKEN") or data.get("token")
    configured = list(data.get("repositories") or [])
    try:
        repositories = list(
            dict.fromkeys(resolve_repository(r, configured) for r in repositories or [])
        )
    except ValueError as error:
        raise SystemExit(str(error)) from error
    repositories = repositories or configured
    if not token:
        raise SystemExit(
            "No token: use --token, $GITHUB_TOKEN or 'token' in the config. "
            "Run 'gh-community config create' to create a config."
        )
    if not repositories:
        raise SystemExit(
            "No repositories: use --repo or 'repositories' in the config. "
            "Run 'gh-community config create' to create a config."
        )
    return Config(token=token, repositories=list(repositories))


def resolve_path(path: Path | None = None) -> Path:
    """The file to edit: path, else the first existing default, else the user file."""
    if path is not None:
        return path
    candidates = (Path("config.yaml"), user_config_path())
    return next((p for p in candidates if p.is_file()), user_config_path())


def read_data(path: Path) -> dict:
    """The raw contents of the file at path; {} if it does not exist."""
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def write_data(path: Path, data: dict) -> None:
    """Write the file; it may hold a token, so only the owner may read it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(mode=0o600)
    path.chmod(0o600)
    path.write_text(yaml.safe_dump(data, sort_keys=False))


def save_config(path: Path, config: Config) -> None:
    """Write a new configuration."""
    data = {"repositories": config.repositories}
    if config.token:
        data = {"token": config.token, **data}
    write_data(path, data)
