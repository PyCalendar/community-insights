from community_insights.github import RateLimit


class Answering:
    """A client that says who it is, with an expiration or not, and which
    repositories it can see (all but o/empty)."""

    def __init__(self, token, expires=None, fail=None):
        """A client that knows its token, when it expires and how it fails."""
        self.token, self.fail = token, fail
        self.rate = RateLimit(expires_at=expires)
        self.requests = 0

    async def viewer(self):
        """The owner of the token, or the error it fails with."""
        if self.fail:
            raise self.fail
        return "kim"

    async def visible(self, names):
        """Every repository but o/empty is visible."""
        return {n: n != "o/empty" for n in names}

    async def close(self):
        """Nothing to close."""
        pass
