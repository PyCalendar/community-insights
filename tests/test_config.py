import stat

import pytest

from gh_community.config import Config, load_config, save_config


def test_roundtrip_and_permissions(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    path = tmp_path / "sub" / "config.yaml"
    save_config(path, Config("secret", ["a/b", "c/d"]))
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    config = load_config(path)
    assert (config.token, config.repositories) == ("secret", ["a/b", "c/d"])


def test_arguments_override_config_and_env(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "env")
    path = tmp_path / "config.yaml"
    save_config(path, Config("file", ["a/b"]))
    assert load_config(path).token == "env"
    config = load_config(path, token="arg", repositories=["x/y"])
    assert (config.token, config.repositories) == ("arg", ["x/y"])


def test_no_file_needed_with_arguments(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert load_config(token="t", repositories=["a/b"]).repositories == ["a/b"]


def test_missing_token_fails(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    path = tmp_path / "c.yaml"
    save_config(path, Config("", ["a/b"]))
    with pytest.raises(SystemExit):
        load_config(path)
