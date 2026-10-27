from .client import FakeClient


class Counting(FakeClient):
    """Answers like the fake; or fails as told."""

    def __init__(self, name, fail=None, **kwargs):
        """A fake client with a name, that can fail."""
        super().__init__(**kwargs)
        self.name, self.fail = name, fail

    async def graphql(self, query, **variables):
        """Fail if asked to, else answer like the fake client."""
        if self.fail:
            raise self.fail
        return await super().graphql(query, **variables)
