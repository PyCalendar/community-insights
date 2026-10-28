"""Decide whether the links of the documentation work, from the result of Sphinx.

``make linkcheck`` runs ``sphinx-build -b linkcheck``, which writes one JSON line per link
into ``docs/_build/linkcheck/output.json``. A server that this machine cannot reach at all
(``Network is unreachable``, such as an address of IPv6 on a runner of GitHub without it)
says nothing about the link, so it is shown, but does not fail the check.

Run it as ``python -m tests.linkchecker.docs docs/_build/linkcheck/output.json``.
"""

import json
import sys
from pathlib import Path

FAILED = {"broken", "timeout"}
UNREACHABLE = ("Network is unreachable",)


def unreachable(row: dict) -> bool:
    """Whether the link could not be checked, because this machine reaches no network.

    Args:
        row: A line of ``output.json``.

    Returns:
        True, if the link is broken only because the network is unreachable.

    Examples:
        >>> unreachable({"status": "broken", "info": "[Errno 101] Network is unreachable"})
        True
        >>> unreachable({"status": "broken", "info": "404 Client Error: Not Found"})
        False
    """
    return row["status"] == "broken" and any(text in row["info"] for text in UNREACHABLE)


def report(lines: list[str]) -> tuple[list[str], list[str]]:
    """Sort the links that did not work into failures and unreachable ones.

    Args:
        lines: The lines of ``output.json``.

    Returns:
        The failures and the unreachable links, each as ``file:line status uri info``.

    Examples:
        >>> report(['{"filename": "a.rst", "lineno": 1, "status": "working", '
        ...         '"code": 0, "uri": "https://example.org/", "info": ""}'])
        ([], [])
    """
    failed, skipped = [], []
    for line in lines:
        if not line.strip():
            continue
        row = json.loads(line)
        text = f"{row['filename']}:{row['lineno']} {row['status']} {row['uri']} {row['info']}"
        if unreachable(row):
            skipped.append(text)
        elif row["status"] in FAILED:
            failed.append(text)
    return failed, skipped


def main(path: str) -> int:
    """Print the links that did not work, after ``sphinx-build`` failed.

    Args:
        path: The file ``output.json`` of Sphinx.

    Returns:
        1 if a link is broken or timed out, or if no unreachable link explains why Sphinx
        failed (such as a warning); 0 if only unreachable links failed.
    """
    failed, skipped = report(Path(path).read_text(encoding="utf-8").splitlines())
    for text in skipped:
        print("Not checked, the network is unreachable:", text)
    for text in failed:
        print("Failed:", text)
    return 1 if failed or not skipped else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
