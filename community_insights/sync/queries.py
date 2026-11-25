"""The GraphQL queries of reading pull requests and issues."""

from ..models import Item

PAGE = 50  # items in one request
INNER = 50  # comments and reviews of an item in the same request
MORE = 100  # comments or reviews in a request for the rest
COMMITS = 10  # the last commits of a pull request: whether its author changed it after feedback
DETAILS = 50  # pull requests in one request for their commits and closers
THREADS = 10  # pull requests in one request for their review threads and suggestions
THREADS_EACH = 50  # review threads of a pull request in the first request; then pages of MORE
THREAD_COMMENTS = 20  # comments of a review thread in the first request; then pages of MORE
APPLY_COMMITS = 100  # commits of a pull request in a request: which applied suggestions
COMMIT_AUTHORS = 100  # authors and co-authors of a commit
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
    state = " state" if field == "reviews" else ""  # an approval needs no reply
    return (
        f"{field}({args}) {{ pageInfo {{ hasNextPage endCursor }} "
        f"nodes {{ {date} author {{ login __typename }} authorAssociation{state} }} }}"
    )


# the last commits with their author, and who closed the pull request
PR_MORE = (
    f"commits(last: {COMMITS}) {{ nodes {{ commit {{"
    " committedDate author { user { login } } } } }"
    " timelineItems(itemTypes: [CLOSED_EVENT], last: 1) {"
    " nodes { ... on ClosedEvent { actor { login } } } }"
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
        f"merged mergedAt mergedBy {{ login }} isDraft {connection('reviews')} {PR_MORE}"
        if kind == Item.PR
        else ""
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


def details_query() -> str:
    """The last commits, the closer, the reviews with their kind and whether it is a draft.

    Returns:
        The query, with the variable ``ids``: the node ids of the pull requests.
    """
    approvals = (
        f"reviews(first: {MORE}, states: [APPROVED, CHANGES_REQUESTED, COMMENTED, DISMISSED])"
        " { nodes { submittedAt state author { login } } }"
    )
    return (
        "query($ids: [ID!]!) { nodes(ids: $ids) { ... on PullRequest { id isDraft "
        f"{PR_MORE} {approvals} }} }} }}"
    )


def thread_comments(first: int, after: bool = False) -> str:
    """The comments of a review thread: the text, the time, the author and the place.

    Args:
        first: How many.
        after: Whether to read after the cursor ``$after``.

    Returns:
        The part of the query.
    """
    args = f"first: {first}" + (", after: $after" if after else "")
    return (
        f"comments({args}) {{ pageInfo {{ hasNextPage endCursor }} nodes {{ databaseId body "
        "url createdAt outdated path author { login } } }"
    )


def review_threads(first: int, after: bool = False) -> str:
    """The review threads of a pull request: resolved by whom, and their first comments.

    Args:
        first: How many.
        after: Whether to read after the cursor ``$after``.

    Returns:
        The part of the query.
    """
    args = f"first: {first}" + (", after: $after" if after else "")
    return (
        f"reviewThreads({args}) {{ pageInfo {{ hasNextPage endCursor }} nodes {{ id "
        f"isResolved resolvedBy {{ login }} {thread_comments(THREAD_COMMENTS)} }} }}"
    )


def pull_commits(after: bool = False) -> str:
    """The commits of a pull request: when and the first line of the message.

    The authors are read only of the commits that applied suggestions
    (``commit_authors_query``): asking them of every commit costs many more points.

    Args:
        after: Whether to read after the cursor ``$after``.

    Returns:
        The part of the query.
    """
    args = f"first: {APPLY_COMMITS}" + (", after: $after" if after else "")
    return (
        f"commits({args}) {{ pageInfo {{ hasNextPage endCursor }} nodes {{ commit {{ "
        "id committedDate messageHeadline } } }"
    )


def commit_authors_query() -> str:
    """The authors and co-authors of commits.

    Returns:
        The query, with the variable ``ids``: the node ids of the commits, at most
        ``APPLY_COMMITS``.
    """
    return (
        "query($ids: [ID!]!) { nodes(ids: $ids) { ... on Commit { id "
        f"authors(first: {COMMIT_AUTHORS}) {{ nodes {{ user {{ login }} }} }} }} }} }}"
    )


def threads_query() -> str:
    """The review threads of pull requests with their comments, and their commits.

    The comments with a code suggestion and whether the thread was resolved, and the commits
    that applied suggestions (``sync.suggestions``). What does not fit is read with
    ``more_threads_query``, ``more_thread_comments_query`` and ``more_pull_commits_query``.

    Returns:
        The query, with the variable ``ids``: the node ids of the pull requests.
    """
    return (
        "query($ids: [ID!]!) { nodes(ids: $ids) { ... on PullRequest { id "
        f"{review_threads(THREADS_EACH)} {pull_commits()} }} }} }}"
    )


def more_threads_query() -> str:
    """The next review threads of a pull request.

    Returns:
        The query, with the variables ``id`` and ``after``.
    """
    return (
        "query($id: ID!, $after: String) { node(id: $id) { ... on PullRequest { "
        f"{review_threads(MORE, True)} }} }} }}"
    )


def more_thread_comments_query() -> str:
    """The next comments of a review thread.

    Returns:
        The query, with the variables ``id`` (of the thread) and ``after``.
    """
    return (
        "query($id: ID!, $after: String) { node(id: $id) { ... on PullRequestReviewThread { "
        f"{thread_comments(MORE, True)} }} }} }}"
    )


def more_pull_commits_query() -> str:
    """The next commits of a pull request.

    Returns:
        The query, with the variables ``id`` and ``after``.
    """
    return (
        "query($id: ID!, $after: String) { node(id: $id) { ... on PullRequest { "
        f"{pull_commits(True)} }} }} }}"
    )
