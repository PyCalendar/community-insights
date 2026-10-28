"""The catalog of the GraphQL queries, checked with gql, without the network."""

import pytest
from gql import gql

from community_insights.github import catalog

SCHEMA = """
type Query { viewer: User!  user(login: String!): User }
type User { login: String!  name: String }
"""


@pytest.mark.parametrize("name", list(catalog.examples()))
def test_every_query_is_graphql(name):
    """gql parses each query the site sends."""
    assert gql(catalog.examples()[name]).document.definitions


def test_valid_queries_have_no_problems():
    """A query that the schema allows has no messages."""
    found = {"me": "query { viewer { login name } }"}
    assert catalog.problems(SCHEMA, found) == {}


@pytest.mark.parametrize(
    ("query", "message"),
    [
        (
            "query { viewer { age } }",
            "Cannot query field 'age' on type 'User'. Did you mean 'name'?",
        ),
        ("query($l: String!) { viewer { login } }", "Variable '$l' is never used."),
        ("query { user(login: 1) { login } }", "String cannot represent a non string value: 1"),
        ("query { viewer { login }", "Syntax Error: Expected Name, found <EOF>."),
    ],
)
def test_problems_are_named(query, message):
    """Unknown fields, unused variables, wrong arguments and broken syntax are found."""
    assert catalog.problems(SCHEMA, {"q": query}) == {"q": [message]}


def test_the_repositories_of_the_viewer_declare_no_owner():
    """The query of the viewer has no variable login, which GitHub calls unused."""
    assert "$login" not in catalog.examples()["repositories of the viewer"]
    assert "$login" in catalog.examples()["repositories of an owner"]
