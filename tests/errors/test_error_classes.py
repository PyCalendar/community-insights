"""Every error has a scope, a title, help and a link to the documentation."""

import pytest
import requests

from community_insights import errors

ALL = errors.all_errors()


@pytest.mark.parametrize("name", sorted(ALL))
def test_every_error_explains_itself(name):
    cls = ALL[name]
    assert cls.title and cls.title != "Something went wrong" or cls is errors.CommunityError
    assert cls.__doc__ and len(cls.__doc__.split()) >= 5, "say what happened and what to do"
    assert cls.docs_url().endswith(f"#{cls.__module__}.{name}")
    assert cls.__module__.startswith("community_insights.errors.")


def test_every_error_is_in_the_documentation():
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
    assert type(errors.translate(raised)) is expected
