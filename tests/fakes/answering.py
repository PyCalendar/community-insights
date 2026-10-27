from community_insights.github import RateLimit


class Answering:
    """A client that says who it is, with an expiration or not, and which
    repositories it can see (all but o/empty)."""

    def __init__(self, token, expires=None, fail=None):
        self.token, self.fail = token, fail
        self.rate = RateLimit(expires_at=expires)
        self.requests = 0

    async def viewer(self):
        if self.fail:
            raise self.fail
        return "kim"

    async def visible(self, names):
        return {n: n != "o/empty" for n in names}

    async def close(self):
        pass
