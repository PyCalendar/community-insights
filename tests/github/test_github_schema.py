"""Every GraphQL query of the site is valid, by the schema of GitHub (``make check-graphql``)."""

import os
from pathlib import Path

import pytest

from community_insights.github import catalog

SCHEMA = os.environ.get("GITHUB_SCHEMA", "")


@pytest.mark.skipif(not SCHEMA, reason="make check-graphql downloads the schema of GitHub")
def test_the_queries_are_valid_for_github():
    """GitHub would accept each query: its fields, arguments and variables exist."""
    assert catalog.problems(Path(SCHEMA).read_text()) == {}
