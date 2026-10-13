"""Command line interface: gh-community."""

from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from .cache import ResponseCache, default_cache_dir
from .config import (
    TOKEN_ACCESS,
    Config,
    load_config,
    read_data,
    resolve_path,
    resolve_repository,
    save_config,
    user_config_path,
    write_data,
)
from .contributors import JOBS, collect, sort_rows, to_markdown

app = typer.Typer(help="GitHub community analysis.", no_args_is_help=True)
contributors_app = typer.Typer(help="Contributor statistics.", no_args_is_help=True)
config_app = typer.Typer(help="Manage the configuration.", no_args_is_help=True)
app.add_typer(contributors_app, name="contributors")
app.add_typer(config_app, name="config")
token_app = typer.Typer(
    help="Manage the stored token.",
    epilog=TOKEN_ACCESS,
    no_args_is_help=True,
)
repo_app = typer.Typer(help="Manage the stored repositories.", no_args_is_help=True)
config_app.add_typer(token_app, name="token")
config_app.add_typer(repo_app, name="repo")


class SortColumn(StrEnum):
    handle = "handle"
    commits = "commits"
    prs = "prs"
    opened = "opened"
    commented = "commented"
    pr_commented = "pr_commented"
    reviewed = "reviewed"
    activity = "activity"


# Options for every command that talks to the GitHub API. They override the config.
ConfigOption = Annotated[
    Path | None, typer.Option("--config", help="Path to the YAML configuration.")
]
TokenOption = Annotated[
    str | None,
    typer.Option("--token", help="GitHub token (default: $GITHUB_TOKEN, then config)."),
]
RepoArgument = Annotated[
    list[str] | None,
    typer.Argument(
        metavar="[OWNER/NAME]...",
        help=(
            "Repositories to analyse, as owner/name or, if the config has "
            "exactly one repository of that name, just the name "
            "(default: the config)."
        ),
    ),
]


CacheDirOption = Annotated[
    Path | None,
    typer.Option(
        "--cache-dir",
        help="Where responses are cached (default: in the temporary directory).",
    ),
]
JobsOption = Annotated[
    int,
    typer.Option("--jobs", min=1, help="Requests to send at the same time."),
]
NoCacheOption = Annotated[
    bool, typer.Option("--no-cache", help="Do not read or write the cache.")
]


@contributors_app.command("all")
def contributors_all(
    repositories: RepoArgument = None,
    config: ConfigOption = None,
    token: TokenOption = None,
    sort: Annotated[
        SortColumn, typer.Option("--sort", help="Column to sort by.")
    ] = SortColumn.prs,
    cache_dir: CacheDirOption = None,
    no_cache: NoCacheOption = False,
    jobs: JobsOption = JOBS,
) -> None:
    """List all contributors as a Markdown table."""
    cfg = load_config(config, token, repositories)
    rows = collect(
        cfg.token,
        cfg.repositories,
        # stderr, so that stdout stays the plain table
        progress=lambda message: typer.echo(message, err=True),
        cache=None if no_cache else ResponseCache(cache_dir or default_cache_dir()),
        jobs=jobs,
    )
    typer.echo(to_markdown(sort_rows(rows, sort.value)))


@config_app.command("create")
def config_create(
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            help="Where to write the configuration "
            "(default: $XDG_CONFIG_HOME/gh-community/config.yaml).",
        ),
    ] = None,
) -> None:
    """Interactively create the configuration file."""
    config = config or user_config_path()
    typer.echo(f"Creating {config}")
    if config.exists() and not typer.confirm(f"{config} exists. Overwrite?"):
        raise typer.Abort()
    typer.echo(TOKEN_ACCESS)
    token = typer.prompt(
        "GitHub token (empty to rely on $GITHUB_TOKEN or --token)",
        default="",
        hide_input=True,
        show_default=False,
    ).strip()
    answer = typer.prompt("Repositories to analyse (owner/name, separated by spaces)")
    repositories = answer.replace(",", " ").split()
    if not repositories:
        raise typer.BadParameter("At least one repository is needed.")
    save_config(config, Config(token, repositories))
    typer.echo(f"Wrote {config}")


# Commands that edit the config use the file given by --config, else the existing
# default one, else the user one (created on write).
EditConfigOption = Annotated[
    Path | None, typer.Option("--config", help="Path to the YAML configuration.")
]


def _mask(token: str) -> str:
    return token[:4] + "*" * 8 + token[-4:] if len(token) > 12 else "*" * len(token)


@token_app.command("set", epilog=TOKEN_ACCESS)
def token_set(
    token: Annotated[
        str | None, typer.Argument(help="Prompted for if omitted.")
    ] = None,
    config: EditConfigOption = None,
) -> None:
    """Store the GitHub token."""
    path = resolve_path(config)
    if token is None:
        typer.echo(TOKEN_ACCESS)
        token = typer.prompt("GitHub token", hide_input=True)
    data = read_data(path)
    write_data(path, data | {"token": token.strip()})
    typer.echo(f"Token stored in {path}")


@token_app.command("delete")
def token_delete(config: EditConfigOption = None) -> None:
    """Remove the stored token."""
    path = resolve_path(config)
    data = read_data(path)
    if "token" not in data:
        typer.echo(f"No token in {path}", err=True)
        raise typer.Exit(1)
    del data["token"]
    write_data(path, data)
    typer.echo(f"Token removed from {path}")


@token_app.command("show")
def token_show(
    config: EditConfigOption = None,
    reveal: Annotated[bool, typer.Option(help="Print the whole token.")] = False,
) -> None:
    """Show the stored token (masked unless --reveal)."""
    token = read_data(resolve_path(config)).get("token")
    if not token:
        typer.echo(f"No token in {resolve_path(config)}", err=True)
        raise typer.Exit(1)
    typer.echo(token if reveal else _mask(token))


def _check_repo(name: str) -> str:
    if "/" not in name:
        raise typer.BadParameter(f"{name!r} is not of the form owner/name.")
    try:
        return resolve_repository(name, [])
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error


@repo_app.command("add")
def repo_add(
    names: Annotated[list[str], typer.Argument(metavar="OWNER/NAME...")],
    config: EditConfigOption = None,
) -> None:
    """Add repositories."""
    names = [_check_repo(n) for n in names]
    path = resolve_path(config)
    data = read_data(path)
    repositories = list(data.get("repositories") or [])
    for name in names:
        if name in repositories:
            typer.echo(f"{name} is already in {path}")
        else:
            repositories.append(name)
            typer.echo(f"Added {name}")
    write_data(path, data | {"repositories": repositories})


@repo_app.command("list")
def repo_list(config: EditConfigOption = None) -> None:
    """List the stored repositories."""
    for name in read_data(resolve_path(config)).get("repositories") or []:
        typer.echo(name)


@repo_app.command("delete")
def repo_delete(
    names: Annotated[list[str], typer.Argument(metavar="OWNER/NAME...")],
    config: EditConfigOption = None,
) -> None:
    """Remove repositories."""
    path = resolve_path(config)
    data = read_data(path)
    repositories = list(data.get("repositories") or [])
    try:
        names = [resolve_repository(n, repositories) for n in names]
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    missing = [n for n in names if n not in repositories]
    if missing:
        typer.echo(f"Not in {path}: {', '.join(missing)}", err=True)
        raise typer.Exit(1)
    remaining = [r for r in repositories if r not in names]
    write_data(path, data | {"repositories": remaining})
    typer.echo(f"Removed {', '.join(names)}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
