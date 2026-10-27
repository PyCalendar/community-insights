"""The links to the documentation of this project lead to its latest version."""

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[2]
DOCS = re.compile(r"https://community-insights\.readthedocs\.io(/[^\s\"'<>)`]*)?")


def tracked_text_files() -> list[Path]:
    """The files git knows of, without the prompts and the binary ones."""
    names = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    files = []
    for name in names:
        path = ROOT / name
        if name.startswith(".prompts/") or not path.is_file():
            continue
        try:
            path.read_text()
        except UnicodeDecodeError:
            continue
        files.append(path)
    return files


FILES = tracked_text_files()


def test_the_files_link_to_the_docs():
    """The files link to the docs."""
    assert any(DOCS.search(path.read_text()) for path in FILES)


@pytest.mark.parametrize("path", FILES, ids=lambda path: str(path.relative_to(ROOT)))
def test_links_lead_to_the_latest_version(path):
    """Links lead to the latest version."""
    for match in DOCS.finditer(path.read_text()):
        assert (match.group(1) or "").startswith("/en/latest/"), match.group(0)


TEMPLATES = sorted((ROOT / "community_insights" / "templates").rglob("*.html"))


@pytest.mark.parametrize("path", TEMPLATES, ids=lambda path: path.name)
def test_templates_do_not_add_the_version_again(path):
    """The address of the documentation already ends with /en/latest/."""
    assert "}}en/latest" not in path.read_text()


@pytest.mark.django_db
@pytest.mark.parametrize("url", ["/", "/about/", "/dashboard/github/"])
def test_pages_link_to_the_latest_version_once(signed_in, url):
    """Pages link to the latest version once."""
    html = signed_in.get(url, follow=True).content.decode()
    assert "readthedocs.io/en/latest/" in html
    assert "en/latest/en/latest" not in html


def test_the_reference_of_queries_lists_every_variable_and_group():
    """The reference of queries lists every variable and group."""
    from community_insights import query

    variables = (ROOT / "docs" / "reference" / "query-variables.rst").read_text()
    for name, (_, kind, _) in query.VARIABLES.items():
        assert f"\n{name}\n{'-' * len(name)}\n\n*{kind}*: " in variables, name
    page = (ROOT / "docs" / "reference" / "queries.rst").read_text()
    for group in query.GROUPS:
        assert f"``{group}``" in page, group
    assert ", ".join(f"``{c}``" for c in query.DEFAULT_COLUMNS) in page


def test_the_examples_of_the_page_are_in_the_reference():
    """The examples of the page are in the reference."""
    from community_insights.views.contributors import EXAMPLES

    page = (ROOT / "docs" / "reference" / "queries.rst").read_text()
    for title, where, sort, last in EXAMPLES:
        row = (
            f"   * - {str(title)[0].lower()}{str(title)[1:]}\n     - ``{where}``\n     - ``{sort}``"
        )
        assert row in page, title
        assert (f"last {last} days" if last else "the one of the page") in page


def test_the_variables_are_in_an_alphabetical_table_that_links_to_each():
    """A rule of AGENTS.md: the reference lists all variables alphabetically, linked."""
    import re

    from community_insights import query

    page = (ROOT / "docs" / "reference" / "query-variables.rst").read_text()
    listed = re.findall(r"^   \* - :ref:`([a-z_]+) <variable-\1>`$", page, re.MULTILINE)
    assert listed == sorted(query.VARIABLES)
    sections = re.findall(r"^\.\. _variable-([a-z_]+):\n\n\1\n-+$", page, re.MULTILINE)
    assert sections == sorted(query.VARIABLES)


def test_the_kinds_of_rules_are_in_an_alphabetical_table_that_links_to_each():
    """The kinds of rules are in an alphabetical table that links to each."""
    import re

    from community_insights.models import ClassRule

    page = (ROOT / "docs" / "reference" / "class-rules.rst").read_text()
    labels = {kind: str(label) for kind, label in ClassRule.KINDS}
    listed = re.findall(r"^   \* - :ref:`(.+) <rule-([a-z]+)>`$", page, re.MULTILINE)
    assert [kind for _, kind in listed] == sorted(labels, key=lambda k: labels[k].lower())
    assert all(labels[kind] == label for label, kind in listed)
    for kind in labels:
        assert f".. _rule-{kind}:" in page, kind
