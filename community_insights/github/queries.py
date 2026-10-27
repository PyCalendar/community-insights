"""The GraphQL queries of the reads."""

REPOSITORY_FIELDS = "nameWithOwner description stargazerCount isPrivate isArchived"
BATCH = 50  # repositories asked about in one request

VIEWER = "query { viewer { login } }"

SUGGESTIONS = """query {
  viewer {
    organizations(first: 100) { nodes { login
      repositories(first: 50, orderBy: {field: STARGAZERS, direction: DESC}) {
        nodes { nameWithOwner stargazerCount isPrivate } } } }
    repositories(first: 100, ownerAffiliations: OWNER,
                 orderBy: {field: STARGAZERS, direction: DESC}) {
      nodes { nameWithOwner stargazerCount isPrivate } }
    repositoriesContributedTo(first: 100, includeUserRepositories: false,
        contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, PULL_REQUEST_REVIEW],
        orderBy: {field: STARGAZERS, direction: DESC}) {
      nodes { nameWithOwner stargazerCount isPrivate } }
  }
}"""

REPOSITORY = (
    "query($owner: String!, $name: String!) { repository(owner: $owner, name: $name)"
    f" {{ {REPOSITORY_FIELDS} }} }}"
)


def escape(text: str) -> str:
    """A string inside a GraphQL query.

    Args:
        text: The text.

    Returns:
        The text with backslashes and quotes escaped.
    """
    return text.replace("\\", "\\\\").replace('"', '\\"')


def repositories(owner: str | None) -> str:
    """A page of the repositories of the viewer (None) or of an owner.

    Args:
        owner: The organisation or user, None for the owner of the token.

    Returns:
        The query, with the variables ``login`` and ``after``.
    """
    if owner is None:
        root, args = "viewer", "ownerAffiliations: OWNER, "
    else:
        root, args = "repositoryOwner(login: $login)", ""
    return f"""
    query($login: String!, $after: String) {{
      {root} {{ repositories(first: 100, after: $after, {args}
            orderBy: {{field: STARGAZERS, direction: DESC}}) {{
        nodes {{ {REPOSITORY_FIELDS} }} pageInfo {{ hasNextPage endCursor }}
      }} }}
    }}"""


def each_repository(full_names: list[str], fields: str) -> str:
    """The fields of several repositories, as r0, r1, ...

    Args:
        full_names: The repositories as ``owner/name``.
        fields: The fields to read of each.

    Returns:
        The query.
    """
    asked = " ".join(
        f'r{i}: repository(owner: "{escape(name.split("/")[0])}", '
        f'name: "{escape(name.split("/", 1)[1])}") {{ {fields} }}'
        for i, name in enumerate(full_names)
    )
    return f"query {{ {asked} }}"


def people(count: int) -> str:
    """name, location and avatar of the users $l0, $l1, ... as u0, u1, ...

    Args:
        count: How many users.

    Returns:
        The query.
    """
    declared = ", ".join(f"$l{i}: String!" for i in range(count))
    fields = "".join(
        f"u{i}: user(login: $l{i}) {{ login name location avatarUrl }} " for i in range(count)
    )
    return f"query({declared}) {{ {fields} }}"
