"""Every GraphQL query the site sends, checked with gql against the schema of GitHub.

The queries are built by functions; ``examples`` builds each of them once. ``make check-graphql``
downloads the schema GitHub publishes and validates them all (see docs/how-to/develop.rst).
"""

from gql import gql
from graphql import GraphQLError, build_schema, validate

from ..models import Item
from ..sync import queries as sync_queries
from . import queries

SCHEMA_URL = "https://docs.github.com/public/fpt/schema.docs.graphql"


def examples() -> dict[str, str]:
    """Each query the site sends, built once, by a name.

    Returns:
        The queries by their names.
    """
    return {
        "viewer": queries.VIEWER,
        "suggestions": queries.SUGGESTIONS,
        "repository": queries.REPOSITORY,
        "repositories of the viewer": queries.repositories(None),
        "repositories of an owner": queries.repositories("pycalendar"),
        "ids of repositories": queries.each_repository(["o/r", 'o/"quoted"'], "id"),
        "totals of repositories": queries.each_repository(
            ["o/r"], "pullRequests { totalCount } issues { totalCount }"
        ),
        "people": queries.people(3),
        "pull requests": sync_queries.list_query(Item.PR),
        "issues": sync_queries.list_query(Item.ISSUE),
        "commits": sync_queries.commits_query(),
        "more comments": sync_queries.more_query("comments"),
        "more reviews": sync_queries.more_query("reviews"),
    }


def problems(schema: str, found: dict[str, str] | None = None) -> dict[str, list[str]]:
    """What is wrong with the queries, by the schema of GitHub.

    Args:
        schema: The schema in the GraphQL schema language, such as GitHub's
            ``schema.docs.graphql``.
        found: The queries by their names, ``examples()`` if None.

    Returns:
        The messages of the queries that have any, by their names; empty if all are valid.

    Examples:
        >>> schema = "type Query { viewer: User! } type User { login: String! }"
        >>> found = {"ok": "query { viewer { login } }", "bad": "query { viewer { age } }"}
        >>> problems(schema, found)
        {'bad': ["Cannot query field 'age' on type 'User'."]}
    """
    # GitHub's own schema breaks rules of deprecation; it is used as it is
    parsed = build_schema(schema, assume_valid=True, assume_valid_sdl=True)
    result = {}
    for name, query in (examples() if found is None else found).items():
        try:
            errors = validate(parsed, gql(query).document)
        except GraphQLError as error:  # not even GraphQL
            errors = [error]
        if errors:
            result[name] = [error.message for error in errors]
    return result
