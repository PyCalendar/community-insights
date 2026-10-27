"""The GraphQL queries of reading pull requests and issues."""

from ..models import Item

PAGE = 50  # items in one request
INNER = 50  # comments and reviews of an item in the same request
MORE = 100  # comments or reviews in a request for the rest
FIELDS = {Item.PR: "pullRequests", Item.ISSUE: "issues"}


def connection(field: str, after: bool = False) -> str:
    """The first comments or reviews of an item, or those after $after.

    Args:
        field: ``comments`` or ``reviews``.
        after: Whether to read after the cursor ``$after``.

    Returns:
        The part of the query.
    """
    date = "createdAt" if field == "comments" else "submittedAt"
    args = "first: $inner" + (", after: $after" if after else "")
    if field == "reviews":
        args += ", states: [APPROVED, CHANGES_REQUESTED, COMMENTED, DISMISSED]"
    return (
        f"{field}({args}) {{ pageInfo {{ hasNextPage endCursor }} "
        f"nodes {{ {date} author {{ login __typename }} authorAssociation }} }}"
    )


def list_query(kind: str) -> str:
    """A page of pull requests or issues, newest change first.

    A page of pull requests or issues with their first comments and reviews, newest change
    first.

    Args:
        kind: ``pr`` or ``issue``.

    Returns:
        The query.
    """
    extra = (
        f"merged mergedAt mergedBy {{ login }} {connection('reviews')}" if kind == Item.PR else ""
    )
    return f"""
query($owner: String!, $name: String!, $after: String, $page: Int!, $inner: Int!) {{
  repository(owner: $owner, name: $name) {{
    {FIELDS[kind]}(first: $page, after: $after,
          orderBy: {{field: UPDATED_AT, direction: DESC}}) {{
      totalCount
      pageInfo {{ hasNextPage endCursor }}
      nodes {{ id number title state createdAt updatedAt closedAt
               author {{ login __typename }} authorAssociation
               {connection("comments")} {extra} }}
    }}
  }}
}}"""


def commits_query() -> str:
    """A page of the history of the default branch, newest first.

    Returns:
        The query, with the variables ``owner``, ``name``, ``after`` and ``since``.
    """
    return """
query($owner: String!, $name: String!, $after: String, $since: GitTimestamp) {
  repository(owner: $owner, name: $name) {
    defaultBranchRef { target { ... on Commit {
      history(first: 100, after: $after, since: $since) {
        totalCount
        pageInfo { hasNextPage endCursor }
        nodes { oid committedDate author { name user { login } } }
      }
    } } }
  }
}"""


def more_query(field: str) -> str:
    """The next comments or reviews of an item.

    Args:
        field: ``comments`` or ``reviews``.

    Returns:
        The query, with the variables ``id``, ``after`` and ``inner``.
    """
    types = ["Issue", "PullRequest"] if field == "comments" else ["PullRequest"]
    on = " ".join(f"... on {t} {{ {connection(field, True)} }}" for t in types)
    return f"query($id: ID!, $after: String, $inner: Int!) {{ node(id: $id) {{ {on} }} }}"
