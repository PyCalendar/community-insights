"""Command line interface: gh-community."""

import re
from datetime import UTC, date, datetime
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
from .contributors import (
    COLUMN_DEFS,
    DEFAULT_COLUMNS,
    JOBS,
    collect,
    parse_columns,
    to_markdown,
)
from .responses import CLASSES, collect_responses, render
from .results import (
    EXPRESSION_HELP,
    VARIABLES,
    keep,
    list_results,
    parse_expression,
    parse_sort,
    read_result,
    remove,
    result_name,
    result_path,
    sort_rows,
    to_csv,
    variable_doc,
    write_result,
)

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


def _complete_sort(incomplete: str) -> list[str]:
    sign = incomplete[:1] if incomplete[:1] in "+-" else ""
    return [
        sign + name
        for name in sorted(VARIABLES)
        if name.startswith(incomplete[len(sign) :])
    ]


def _checked_sort(sort: str) -> str:
    """The sort, or a usage error; checked before anything is downloaded."""
    try:
        parse_sort(sort)
    except ValueError as error:
        raise typer.BadParameter(str(error), param_hint="--sort") from error
    return sort


CsvOption = Annotated[
    bool,
    typer.Option(
        "--csv",
        help="Print CSV instead of a Markdown table: the headers of the columns as "
        "in the table, then only numbers (not X/total, days instead of the text) "
        "and strings.",
    ),
]
SortOption = Annotated[
    str,
    typer.Option(
        "--sort",
        metavar="[+-]VARIABLE",
        autocompletion=_complete_sort,
        help="What to sort by: +variable ascending, -variable descending (use "
        "--sort=-variable). Without a sign the handle and the days_ are "
        "ascending, the rest descending. Any variable, see below.",
    ),
]


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
    sort: SortOption = "prs_merged",
    csv_output: CsvOption = False,
    cache_dir: CacheDirOption = None,
    no_cache: NoCacheOption = False,
    jobs: JobsOption = JOBS,
    save: Annotated[
        bool, typer.Option(help="Store the result as CSV next to the config.")
    ] = True,
) -> None:
    """List all contributors as a Markdown table.

    The result is also stored as org-repo-yyyy-mm-dd-hh-mm-ss.csv next to the
    config, for 'gh-community result'.
    """
    _checked_sort(sort)
    cfg = load_config(config, token, repositories)
    rows = collect(
        cfg.token,
        cfg.repositories,
        # stderr, so that stdout stays the plain table
        progress=lambda message: typer.echo(message, err=True),
        cache=None if no_cache else ResponseCache(cache_dir or default_cache_dir()),
        jobs=jobs,
    )
    if save:
        path = result_path(
            resolve_path(config).parent,
            result_name(cfg.repositories, datetime.now()),
        )
        write_result(path, rows)
        typer.echo(f"Stored {path}", err=True)
    rows = sort_rows(rows, sort)
    if csv_output:
        typer.echo(to_csv(rows, DEFAULT_COLUMNS), nl=False)
    else:
        typer.echo(to_markdown(rows))


RESPONSE_COLORS = dict(zip(CLASSES, ("yellow", "magenta", "green"), strict=True))


@app.command("response")
def response(
    repositories: RepoArgument = None,
    config: ConfigOption = None,
    token: TokenOption = None,
    cache_dir: CacheDirOption = None,
    no_cache: NoCacheOption = False,
    jobs: JobsOption = JOBS,
    since: Annotated[
        str | None,
        typer.Option(
            "--since",
            metavar="YYYY-MM-DD",
            help="Only pull requests and issues created on or after this date.",
        ),
    ] = None,
) -> None:
    """Show how long pull requests and issues wait for their first response.

    Two bar charts, one for the pull requests and one for the issues, with a
    column for each time up to 1h 3h 6h 12h 24h 2d 3d 5d 1w 2w 3w. Each is counted
    once, by who responded first: a bot, an external person (not owner, member
    or collaborator) or a collaborator or higher. Comments, comments on the
    changes and reviews of someone else than the author are responses.
    """
    try:
        first_day = date.fromisoformat(since) if since else None
    except ValueError as error:
        raise typer.BadParameter(
            f"{since!r} is not a date like 2026-01-31.", param_hint="--since"
        ) from error
    cfg = load_config(config, token, repositories)
    found = collect_responses(
        cfg.token,
        cfg.repositories,
        progress=lambda message: typer.echo(message, err=True),
        cache=None if no_cache else ResponseCache(cache_dir or default_cache_dir()),
        jobs=jobs,
        since=first_day,
    )
    suffix = f" since {since}" if since else ""

    def paint(text: str, kind: str) -> str:
        return typer.style(text, fg=RESPONSE_COLORS[kind])

    for position, (kind, title) in enumerate(
        (("prs", "Pull requests"), ("issues", "Issues"))
    ):
        if position:
            typer.echo()
        typer.echo("\n".join(render(title + suffix, found[kind], paint)))


def _complete_result(ctx: typer.Context, incomplete: str) -> list[str]:
    config = ctx.params.get("config")  # a str here; only if given before the name
    directory = resolve_path(Path(config) if config else None).parent
    return [n for n in list_results(directory) if n.startswith(incomplete)]


def _complete_expression(incomplete: str) -> list[str]:
    """Complete the last word of an expression: a field, and, or, not."""
    head = incomplete.rstrip("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_")
    prefix = incomplete[len(head) :]
    words = [*VARIABLES, "and", "or", "not"]
    return [head + w for w in words if w.startswith(prefix.lower())]


# columns that show their variable differently
COLUMN_NOTES = {
    name: f"{variable_doc(name)}, shown as X/{total} (variable {name}: the number)"
    for name, total in (
        ("prs_open", "prs_total"),
        ("prs_merged", "prs_total"),
        ("prs_unmerged", "prs_total"),
        ("prs_closed", "prs_total"),
        ("issues_open", "issues_opened"),
        ("issues_closed", "issues_opened"),
    )
} | {
    "days_first": "days since the first activity, shown "
    "as N days (variable days_first: N)",
    "days_last": "days since the last activity, shown "
    "as N days (variable days_last: N)",
}


def _column_help() -> str:
    def lines(names) -> str:
        out = []
        for name in names:
            note = COLUMN_NOTES.get(name)
            if note is None:
                note = f"{variable_doc(name)} (also a variable)"
            out.append(f"  {name:<22}{note}")
        return "\n".join(out)

    others = sorted(set(COLUMN_DEFS) - set(DEFAULT_COLUMNS))
    return (
        f"Default columns:\n{lines(DEFAULT_COLUMNS)}\n\n"
        f"Additional columns:\n{lines(others)}"
    )


def _complete_columns(incomplete: str) -> list[str]:
    """Complete the last column name of a specification like +x-y."""
    prefix = re.split(r"(?<=[+-])", incomplete)[-1]
    head = incomplete[: len(incomplete) - len(prefix)]
    return [head + c for c in COLUMN_DEFS if c.startswith(prefix)]


@app.command(
    "result",
    epilog=f"{_column_help()}\n\n{EXPRESSION_HELP}".replace("[bot]", r"\[bot]"),
)
def result(
    name: Annotated[
        str | None,
        typer.Argument(
            help="A stored result, org-repo-yyyy-mm-dd-hh-mm-ss (see --list).",
            autocompletion=_complete_result,
        ),
    ] = None,
    expression: Annotated[
        str | None,
        typer.Argument(
            metavar="[EXPRESSION]",
            autocompletion=_complete_expression,
            help="Show only the contributors for which this is true, for example "
            "'days<30' (see below).",
        ),
    ] = None,
    config: ConfigOption = None,
    list_names: Annotated[
        bool, typer.Option("--list", help="List the names of the stored results.")
    ] = False,
    remove_matching: Annotated[
        list[str] | None,
        typer.Option(
            "--remove",
            metavar="EXPRESSION",
            autocompletion=_complete_expression,
            help="Like EXPRESSION, but removes the contributors for which this is "
            "true instead of keeping them. Can be repeated.",
        ),
    ] = None,
    sort: SortOption = "prs_merged",
    csv_output: CsvOption = False,
    columns: Annotated[
        str | None,
        typer.Option(
            "--columns",
            metavar="[+-]COLUMN...",
            autocompletion=_complete_columns,
            help="The columns to show, as column+column..., in this order, or "
            "+column-column... to add to and remove from the default columns "
            "(use --columns=-column if it starts with -; explained below).",
        ),
    ] = None,
) -> None:
    """Show a stored result as a Markdown table, optionally filtered.

    The filters only change what is printed, the stored file is never edited.
    --list lists the names of the stored results instead.
    """
    _checked_sort(sort)
    directory = resolve_path(config).parent
    if list_names:
        for stored in list_results(directory):
            typer.echo(stored)
        return
    if name is None:
        raise typer.BadParameter("Give the name of a result or use --list.")
    path = result_path(directory, name)
    if not path.is_file():
        raise typer.BadParameter(f"No such result: {path}", param_hint="NAME")
    try:
        keeping = [parse_expression(expression)] if expression else []
    except ValueError as error:
        raise typer.BadParameter(str(error), param_hint="EXPRESSION") from error
    try:
        removing = [parse_expression(e) for e in remove_matching or []]
    except ValueError as error:
        raise typer.BadParameter(str(error), param_hint="--remove") from error
    try:
        shown = list(DEFAULT_COLUMNS) if columns is None else parse_columns(columns)
    except ValueError as error:
        raise typer.BadParameter(str(error), param_hint="--columns") from error
    now = datetime.now(UTC)
    everyone = read_result(path)
    rows = remove(keep(everyone, keeping, now), removing, now)
    rows = sort_rows(rows, sort, now)
    summary = f"Showing {len(rows)} of {len(everyone)} contributors."
    if csv_output:
        typer.echo(to_csv(rows, shown, now), nl=False)
        typer.echo(summary, err=True)  # stdout stays the CSV
    else:
        typer.echo(to_markdown(rows, now, shown))
        typer.echo(f"\n{summary}")


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
