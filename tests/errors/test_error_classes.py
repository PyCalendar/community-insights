"""Every error has a scope, a title, help and a link to the documentation."""

import re

import pytest
import requests

from community_insights import errors

ALL = errors.all_errors()


@pytest.mark.parametrize("name", sorted(ALL))
def test_every_error_explains_itself(name):
    """Every error explains itself."""
    cls = ALL[name]
    assert cls.title and cls.title != "Something went wrong" or cls is errors.CommunityError
    assert cls.__doc__ and len(cls.__doc__.split()) >= 5, "say what happened and what to do"
    assert cls.docs_url().endswith(f"#{cls.__module__}.{name}")
    assert cls.__module__.startswith("community_insights.errors.")


def test_every_error_is_in_the_documentation():
    """Every error is in the documentation."""
    from pathlib import Path

    reference = (
        Path(__file__).parent.parent.parent / "docs" / "reference" / "errors.rst"
    ).read_text()
    for module in {cls.__module__ for cls in ALL.values()}:
        assert f"automodule:: {module}" in reference, module


@pytest.mark.parametrize(
    ("raised", "expected"),
    [
        (requests.ConnectionError("down"), errors.GitHubUnreachable),
        (requests.Timeout("slow"), errors.GitHubUnreachable),
        (requests.HTTPError("x"), errors.GitHubError),
        (ValueError("bad"), errors.InvalidInput),
        (KeyError("k"), errors.UnexpectedError),
        (errors.ExpiredAPIToken("x"), errors.ExpiredAPIToken),
    ],
)
def test_translation_table(raised, expected):
    """Translation table."""
    assert type(errors.translate(raised)) is expected


def test_the_errors_of_queries_link_to_how_to_write_a_query():
    """The errors of queries link to how to write a query."""
    from community_insights.errors import InvalidQuery, all_errors

    query_errors = [cls for cls in all_errors().values() if issubclass(cls, InvalidQuery)]
    assert len(query_errors) > 5
    for cls in query_errors:
        assert ":doc:`/how-to/queries`" in cls.__doc__, cls.__name__


# errors without a page of the documentation that explains them; listed in todo.txt to review
WITHOUT_GUIDE = {"InvalidInput"}


def test_the_errors_of_queries_name_the_page_that_explains_queries():
    """The errors of queries name the page that explains queries."""
    from community_insights.errors import InvalidQuery, UnknownGroup, UnknownVariable, all_errors

    for cls in all_errors().values():
        if issubclass(cls, InvalidQuery):
            assert "/en/latest/reference/quer" in cls.guide_url(), cls.__name__
            assert ":doc:`/how-to/queries`" in cls.__doc__, cls.__name__
    assert UnknownVariable.guide_url().endswith("reference/query-variables.html")
    assert UnknownGroup.guide_url().endswith("reference/queries.html#group-by")


def test_every_error_links_to_the_page_it_refers_to():
    """The site shows the guide; the description in the documentation links to it, too."""
    from pathlib import Path

    from community_insights.errors import all_errors

    docs = Path(__file__).parents[2] / "docs"
    for name, cls in all_errors().items():
        if name in WITHOUT_GUIDE:
            assert cls.guide_url() == "", name
            continue
        page, _, anchor = cls.guide.partition("#")
        page = page.removesuffix(".html")
        source = docs / f"{page}.rst"
        assert source.is_file(), (name, page)
        links = (f":doc:`/{page}`", f":ref:`{anchor}`" if anchor else None)
        assert any(link and link in cls.__doc__ for link in links), f"{name}: link {page}"
        assert str(cls.guide_title), name
        if anchor:
            text = source.read_text()
            headings = re.findall(r"^(.+)\n[=~-]{3,}$", text, re.MULTILINE)
            ids = {re.sub(r"[^a-z0-9]+", "-", h.lower()).strip("-") for h in headings}
            assert anchor in ids or f".. _{anchor}:" in text, (name, anchor)
