import pytest
from rows import blank
from typer.testing import CliRunner

from gh_community import cli
from gh_community.config import Config, save_config

runner = CliRunner()


def row(handle, commits, prs, merged):
    return blank(
        user_handle=handle,
        commits_total=commits,
        prs_total=prs,
        prs_merged=merged,
    )


ROWS = [
    row("bob", 5, 120, 100),
    row("alexander", 1200, 3, 2),
]


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.setattr(cli, "default_cache_dir", lambda: tmp_path / "cache")
    calls = []

    def fake_collect(token, repositories, progress=None, cache=None, jobs=None):
        progress("working")
        calls.append((token, list(repositories)))
        return [dict(r) for r in ROWS]

    monkeypatch.setattr(cli, "collect", fake_collect)
    return calls


def handles(output):
    lines = output.splitlines()
    if "" in lines:  # the summary after the table
        lines = lines[: lines.index("")]
    return [line.split("|")[1].strip() for line in lines[2:]]


def test_all_default_sort_merged_prs(isolated):
    result = runner.invoke(cli.app, ["contributors", "all", "a/b", "--token", "t"])
    assert result.exit_code == 0, result.output
    assert handles(result.stdout) == ["bob", "alexander"]
    assert isolated == [("t", ["a/b"])]


def test_sort_prs_and_handle():
    base = ["contributors", "all", "--token", "t", "a/b", "--sort"]
    assert handles(runner.invoke(cli.app, [*base, "prs_merged"]).stdout) == [
        "bob",
        "alexander",
    ]
    assert handles(runner.invoke(cli.app, [*base, "commits_total"]).stdout) == [
        "alexander",
        "bob",
    ]
    assert handles(runner.invoke(cli.app, [*base, "user_handle"]).stdout) == [
        "alexander",
        "bob",
    ]


def test_invalid_sort_column():
    result = runner.invoke(cli.app, ["contributors", "all", "--sort", "nope"])
    assert result.exit_code == 2


def test_cli_overrides_config_and_env(tmp_path, monkeypatch, isolated):
    path = tmp_path / "c.yaml"
    save_config(path, Config("file", ["file/repo"]))
    runner.invoke(cli.app, ["contributors", "all", "--config", str(path)])
    monkeypatch.setenv("GITHUB_TOKEN", "env")
    runner.invoke(cli.app, ["contributors", "all", "--config", str(path)])
    runner.invoke(
        cli.app,
        [
            "contributors",
            "all",
            "--config",
            str(path),
            "--token",
            "arg",
            "x/y",
            "z/w",
        ],
    )
    assert isolated == [
        ("file", ["file/repo"]),
        ("env", ["file/repo"]),
        ("arg", ["x/y", "z/w"]),
    ]


def test_missing_config_file_fails(tmp_path):
    result = runner.invoke(cli.app, ["contributors", "all", "--config", "nope.yaml"])
    assert result.exit_code != 0
    assert "not found" in result.output


def test_no_token_fails():
    result = runner.invoke(cli.app, ["contributors", "all", "a/b"])
    assert result.exit_code != 0
    assert "No token" in result.output


def test_config_create(tmp_path):
    path = tmp_path / "new" / "config.yaml"
    result = runner.invoke(
        cli.app, ["config", "create", "--config", str(path)], input="secret\na/b, c/d\n"
    )
    assert result.exit_code == 0, result.output
    assert path.stat().st_mode & 0o777 == 0o600
    result = runner.invoke(cli.app, ["contributors", "all", "--config", str(path)])
    assert result.exit_code == 0


def test_config_create_overwrite_declined(tmp_path):
    path = tmp_path / "c.yaml"
    save_config(path, Config("keep", ["a/b"]))
    result = runner.invoke(
        cli.app, ["config", "create", "--config", str(path)], input="n\n"
    )
    assert result.exit_code != 0
    assert "keep" in path.read_text()


def test_config_create_requires_repository(tmp_path):
    path = tmp_path / "c.yaml"
    result = runner.invoke(
        cli.app, ["config", "create", "--config", str(path)], input="\n  \n"
    )
    assert result.exit_code != 0
    assert not path.exists()


def test_config_create_default_location_uses_xdg(tmp_path):
    result = runner.invoke(cli.app, ["config", "create"], input="t\na/b\n")
    path = tmp_path / "xdg" / "gh-community" / "config.yaml"
    assert result.exit_code == 0, result.output
    assert path.is_file()
    assert result.output.count(str(path)) == 2  # announced, then confirmed


def test_config_create_falls_back_to_home(tmp_path, monkeypatch):
    monkeypatch.delenv("XDG_CONFIG_HOME")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    result = runner.invoke(cli.app, ["config", "create"], input="t\na/b\n")
    assert (tmp_path / "home/.config/gh-community/config.yaml").is_file(), result.output


@pytest.mark.parametrize(
    ("words", "cword", "expected"),
    [
        ("gh-community ", 1, {"contributors", "config"}),
        ("gh-community config ", 2, {"create"}),
        ("gh-community contributors ", 2, {"all"}),
        ("gh-community config create --", 3, {"--config", "--help"}),
    ],
)
def test_shell_completion(monkeypatch, words, cword, expected):
    monkeypatch.setenv("_GH_COMMUNITY_COMPLETE", "complete_bash")
    monkeypatch.setenv("COMP_WORDS", words)
    monkeypatch.setenv("COMP_CWORD", str(cword))
    result = runner.invoke(cli.app, [], prog_name="gh-community")
    assert expected <= set(result.output.split())


def run(*args, input=None):
    return runner.invoke(cli.app, list(args), input=input)


def test_token_set_show_delete(tmp_path):
    path = str(tmp_path / "c.yaml")
    assert (
        run(
            "config", "token", "set", "ghp_1234567890abcdef", "--config", path
        ).exit_code
        == 0
    )
    assert (tmp_path / "c.yaml").stat().st_mode & 0o777 == 0o600
    shown = run("config", "token", "show", "--config", path).output.strip()
    assert shown == "ghp_********cdef"
    assert (
        run("config", "token", "show", "--reveal", "--config", path).output.strip()
        == "ghp_1234567890abcdef"
    )
    assert run("config", "token", "delete", "--config", path).exit_code == 0
    assert run("config", "token", "show", "--config", path).exit_code == 1
    assert run("config", "token", "delete", "--config", path).exit_code == 1


def test_token_set_prompts_and_keeps_repositories(tmp_path):
    path = tmp_path / "c.yaml"
    save_config(path, Config("old", ["a/b"]))
    result = run("config", "token", "set", "--config", str(path), input="new\n")
    assert result.exit_code == 0, result.output
    assert (
        run("config", "token", "show", "--reveal", "--config", str(path)).output.strip()
        == "new"
    )
    assert run("config", "repo", "list", "--config", str(path)).output.split() == [
        "a/b"
    ]


def test_repo_add_list_delete(tmp_path):
    path = str(tmp_path / "c.yaml")
    assert run("config", "repo", "add", "a/b", "c/d", "--config", path).exit_code == 0
    again = run("config", "repo", "add", "a/b", "--config", path)
    assert "already" in again.output
    assert run("config", "repo", "list", "--config", path).output.split() == [
        "a/b",
        "c/d",
    ]
    assert run("config", "repo", "delete", "a/b", "--config", path).exit_code == 0
    assert run("config", "repo", "list", "--config", path).output.split() == ["c/d"]
    missing = run("config", "repo", "delete", "x/y", "--config", path)
    assert missing.exit_code == 1
    assert run("config", "repo", "list", "--config", path).output.split() == ["c/d"]


def test_repo_add_validates_name(tmp_path):
    path = tmp_path / "c.yaml"
    result = run("config", "repo", "add", "nonsense", "--config", str(path))
    assert result.exit_code == 2
    assert not path.exists()


def test_edit_defaults_to_xdg_file(tmp_path):
    assert run("config", "repo", "add", "a/b").exit_code == 0
    assert (tmp_path / "xdg" / "gh-community" / "config.yaml").is_file()
    assert run("config", "repo", "list").output.split() == ["a/b"]


def test_short_names_resolved_from_config(tmp_path, isolated):
    path = tmp_path / "c.yaml"
    save_config(path, Config("t", ["org/alpha", "org/beta", "me/gamma"]))
    result = run(
        "contributors", "all", "alpha", "me/other", "GAMMA", "--config", str(path)
    )
    assert result.exit_code == 0, result.output
    assert isolated == [("t", ["org/alpha", "me/other", "me/gamma"])]


def test_short_name_ambiguous_or_unknown(tmp_path, isolated):
    path = tmp_path / "c.yaml"
    save_config(path, Config("t", ["org/same", "me/same", "org/beta"]))
    ambiguous = run("contributors", "all", "same", "--config", str(path))
    assert ambiguous.exit_code != 0
    assert "ambiguous" in ambiguous.output and "org/same" in ambiguous.output
    unknown = run("contributors", "all", "nope", "--config", str(path))
    assert unknown.exit_code != 0
    assert "owner/name" in unknown.output
    assert isolated == []


def test_short_name_without_config_fails(isolated):
    result = run("contributors", "all", "alpha", "--token", "t")
    assert result.exit_code != 0
    assert isolated == []


def test_repo_delete_short_name(tmp_path):
    path = str(tmp_path / "c.yaml")
    run("config", "repo", "add", "org/alpha", "me/beta", "--config", path)
    assert run("config", "repo", "delete", "alpha", "--config", path).exit_code == 0
    assert run("config", "repo", "list", "--config", path).output.split() == ["me/beta"]
    assert run("config", "repo", "delete", "nope", "--config", path).exit_code != 0


def test_repo_add_needs_long_form(tmp_path):
    result = run("config", "repo", "add", "alpha", "--config", str(tmp_path / "c.yaml"))
    assert result.exit_code == 2


def test_token_access_documented():
    assert "read access" in run("config", "token", "--help").output
    created = run("config", "create", input="t\na/b\n").output
    assert "read access" in created
    assert "read access" in run("config", "token", "set", input="t\n").output
    assert "read access" not in run("config", "token", "set", "t").output


def test_token_set_help_documents_access():
    assert "read access" in run("config", "token", "set", "--help").output


def test_progress_goes_to_stderr_not_stdout():
    result = runner.invoke(cli.app, ["contributors", "all", "a/b", "--token", "t"])
    assert result.stderr.splitlines()[0] == "working"
    assert "working" not in result.stdout
    assert result.stdout.startswith("| handle")


def test_jobs_option(monkeypatch):
    seen = []
    monkeypatch.setattr(
        cli, "collect", lambda *args, **kwargs: seen.append(kwargs["jobs"]) or []
    )
    run("contributors", "all", "a/b", "--token", "t")
    run("contributors", "all", "a/b", "--token", "t", "--jobs", "7")
    assert seen == [cli.JOBS, 7]
    assert (
        run("contributors", "all", "a/b", "--token", "t", "--jobs", "0").exit_code == 2
    )


def test_all_stores_csv_next_to_config_and_result_filters(tmp_path):
    config = tmp_path / "conf" / "config.yaml"
    save_config(config, Config("t", ["collective/icalendar"]))
    result = runner.invoke(cli.app, ["contributors", "all", "--config", str(config)])
    assert result.exit_code == 0, result.output
    (stored,) = (tmp_path / "conf").glob("collective-icalendar-*.csv")
    assert handles(result.stdout) == ["bob", "alexander"]

    name = stored.stem
    listed = runner.invoke(cli.app, ["result", "--list", "--config", str(config)])
    assert runner.invoke(cli.app, ["result", "--config", str(config)]).exit_code != 0
    assert listed.stdout.split() == [name]
    shown = runner.invoke(cli.app, ["result", name, "--config", str(config)])
    assert handles(shown.stdout) == ["bob", "alexander"]
    base = ["result", name, "--config", str(config)]
    # activity is unknown in ROWS, so days is infinite
    shown = runner.invoke(cli.app, [*base, "days_last < 30"])
    assert handles(shown.stdout) == []
    shown = runner.invoke(cli.app, [*base, "commits_total > 100"])
    assert handles(shown.stdout) == ["alexander"]
    assert shown.stdout.splitlines()[-1] == "Showing 1 of 2 contributors."
    old = runner.invoke(cli.app, [*base, "--remove", "days_last > 30"])
    assert handles(old.stdout) == []
    expression = "commits_total > 100 or (prs_merged < 10 and not prs_total >= 120)"
    shown = runner.invoke(cli.app, [*base, "--remove", expression])
    assert handles(shown.stdout) == ["bob"]
    bad = runner.invoke(cli.app, [*base, "--remove", "prs_merged <"])
    assert bad.exit_code != 0


def test_result_name_completion(tmp_path):
    config = tmp_path / "config.yaml"
    for stem in ("a-b-2026-10-13-12-00-00", "x-y-2026-01-01-00-00-00"):
        (tmp_path / f"{stem}.csv").touch()
    ctx = cli.typer.Context(cli.typer.main.get_command(cli.app))
    ctx.params = {"config": str(config)}
    assert cli._complete_result(ctx, "a-") == ["a-b-2026-10-13-12-00-00"]


def test_expression_completion():
    assert cli._complete_expression("prs_merged<10 and prs_rev") == [
        "prs_merged<10 and prs_reviewed"
    ]
    assert cli._complete_expression("(days < 5 or") == ["(days < 5 or"]
    assert "commits_total" in cli._complete_expression("")


def test_result_columns(tmp_path):
    config = tmp_path / "config.yaml"
    save_config(config, Config("t", ["a/b"]))
    runner.invoke(cli.app, ["contributors", "all", "--config", str(config)])
    (stored,) = tmp_path.glob("a-b-*.csv")
    base = ["result", stored.stem, "--config", str(config)]
    shown = runner.invoke(
        cli.app, [*base, "--columns", "user_handle+prs_merged+days_last"]
    )
    assert shown.stdout.splitlines()[0] == "| handle    | merged PRs | last activity |"
    changed = runner.invoke(cli.app, [*base, "--columns", "+prs_open-days_last"])
    assert changed.stdout.splitlines()[0].endswith("| PRs reviewed | open PRs |")
    for bad_spec in ("user_handle+nope", "user_handle,prs_open", "", "x y"):
        bad = runner.invoke(cli.app, [*base, "--columns", bad_spec])
        assert bad.exit_code != 0, bad_spec
    assert cli._complete_columns("user_handle+prs_ap") == ["user_handle+prs_approved"]
    assert cli._complete_columns("+commits_total-prs_o") == ["+commits_total-prs_open"]
    assert cli._complete_columns("user_ass") == ["user_association"]


def test_help_explains_columns_and_variables():
    text = runner.invoke(cli.app, ["result", "--help"], terminal_width=200).stdout
    flat = " ".join(text.split())
    for column in cli.COLUMN_DEFS:
        assert f" {column} " in flat
    assert "pull requests opened and merged, shown as X/prs_total" in flat
    assert "months with any activity (also a variable)" in flat
    assert (
        "days since the last activity, shown as N days (variable days_last: N)" in flat
    )


def test_sort_with_sign_and_unknown_sort(tmp_path):
    config = tmp_path / "config.yaml"
    save_config(config, Config("t", ["a/b"]))
    base = ["contributors", "all", "--config", str(config)]
    for sort, expected in (
        ("--sort=+commits_total", ["bob", "alexander"]),
        ("--sort=-commits_total", ["alexander", "bob"]),
    ):
        assert handles(runner.invoke(cli.app, [*base, sort]).stdout) == expected
    # a value that starts with - after a space
    shown = runner.invoke(cli.app, [*base, "--sort", "-commits_total"])
    assert handles(shown.stdout) == ["alexander", "bob"]
    bad = runner.invoke(cli.app, [*base, "--sort", "+commit_total"], terminal_width=400)
    assert bad.exit_code != 0
    assert "Did you mean 'commits_total'" in " ".join(
        bad.output.replace("│", "").split()
    )
    assert cli._complete_sort("-days_l") == ["-days_last"]


def test_csv_output(tmp_path):
    config = tmp_path / "config.yaml"
    save_config(config, Config("t", ["a/b"]))
    shown = runner.invoke(
        cli.app, ["contributors", "all", "a/b", "--config", str(config)]
    )
    assert shown.exit_code == 0
    name = next(tmp_path.glob("a-b-*.csv")).stem
    base = ["result", name, "--config", str(config), "--csv"]
    result = runner.invoke(cli.app, [*base, "--columns", "user_handle+prs_merged"])
    assert result.stdout == "handle,merged PRs\nbob,100\nalexander,2\n"
    assert result.stderr.strip() == "Showing 2 of 2 contributors."
    again = runner.invoke(
        cli.app,
        ["contributors", "all", "a/b", "--csv", "--no-save", "--config", str(config)],
    )
    assert again.stdout.splitlines()[0].startswith("handle,commits,merged PRs")
    assert "/" not in again.stdout
