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
    """A string inside a GraphQL query."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def repositories(owner: str | None) -> str:
    """A page of the repositories of the viewer (None) or of an owner."""
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
    """The fields of several repositories, as r0, r1, ..."""
    asked = " ".join(
        f'r{i}: repository(owner: "{escape(name.split("/")[0])}", '
        f'name: "{escape(name.split("/", 1)[1])}") {{ {fields} }}'
        for i, name in enumerate(full_names)
    )
    return f"query {{ {asked} }}"


def people(count: int) -> str:
    """name, location and avatar of the users $l0, $l1, ... as u0, u1, ..."""
    declared = ", ".join(f"$l{i}: String!" for i in range(count))
    fields = "".join(
        f"u{i}: user(login: $l{i}) {{ login name location avatarUrl }} " for i in range(count)
    )
    return f"query({declared}) {{ {fields} }}"
