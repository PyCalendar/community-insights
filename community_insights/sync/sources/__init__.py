"""Where the Syncer reads pull requests and issues from.

Where the Syncer reads pull requests and issues from: GraphQL with tokens, or REST without a token.
"""

from .anonymous import AnonymousSource
from .graphql import GraphQLSource

__all__ = ["AnonymousSource", "GraphQLSource"]
