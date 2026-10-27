class Response:
    """An answer of the HTTP session, to test the real client."""

    def __init__(self, status=200, body=None, headers=None, text=""):
        """An HTTP answer with a status, a body, headers and a text."""
        self.status_code, self.body, self.headers, self.text = (
            status,
            body or {},
            headers or {},
            text,
        )

    def json(self):
        """The body, or its error if it is no JSON."""
        if isinstance(self.body, Exception):
            raise self.body
        return self.body
