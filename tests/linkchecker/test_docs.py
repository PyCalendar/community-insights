"""The result of ``make linkcheck``: unreachable servers do not fail it."""

import json

import pytest

from tests.linkchecker import docs

UNREACHABLE = (
    "HTTPSConnectionPool(host='www.gnu.org', port=443): Max retries exceeded with url: "
    "/software/gettext/ (Caused by NewConnectionError(\"HTTPSConnection(host='www.gnu.org', "
    'port=443): Failed to establish a new connection: [Errno 101] Network is unreachable"))'
)


def row(status, info="", uri="https://example.org/"):
    """A line of output.json."""
    return json.dumps(
        {
            "filename": "how-to/translate.rst",
            "lineno": 19,
            "status": status,
            "code": 0,
            "uri": uri,
            "info": info,
        }
    )


def run(tmp_path, *rows):
    """Write the lines into output.json and decide."""
    path = tmp_path / "output.json"
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return docs.main(str(path))


def test_only_unreachable_passes(tmp_path, capsys):
    """A link that only fails because the network is unreachable is listed, but passes."""
    assert run(tmp_path, row("working"), row("broken", UNREACHABLE)) == 0
    assert "Not checked, the network is unreachable: how-to/translate.rst:19" in (
        capsys.readouterr().out
    )


@pytest.mark.parametrize(
    "failure",
    [row("broken", "404 Client Error: Not Found"), row("timeout", "Read timed out.")],
)
def test_broken_or_timeout_fails_also_next_to_unreachable(tmp_path, capsys, failure):
    """A broken link or a timeout fails, also next to an unreachable one."""
    assert run(tmp_path, row("broken", UNREACHABLE), failure) == 1
    assert "Failed: how-to/translate.rst:19" in capsys.readouterr().out


def test_failure_without_unreachable_link_fails(tmp_path):
    """Sphinx failed for another reason, such as a warning: the check fails."""
    assert run(tmp_path, row("working"), row("redirected", uri="https://a.org/")) == 1


@pytest.mark.parametrize("rows", [[], [""], [row("ignored"), row("unchecked"), row("redirected")]])
def test_nothing_failed(rows):
    """Working, ignored, unchecked and redirected links and empty lines are no failure."""
    assert docs.report(rows) == ([], [])


def test_unreachable_needs_broken_status():
    """Only a broken link counts as unreachable."""
    assert not docs.unreachable({"status": "timeout", "info": "Network is unreachable"})
