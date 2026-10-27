class Response:
    """An answer of the HTTP session, to test the real client."""

    def __init__(self, status=200, body=None, headers=None, text=""):
        self.status_code, self.body, self.headers, self.text = (
            status,
            body or {},
            headers or {},
            text,
        )

    def json(self):
        if isinstance(self.body, Exception):
            raise self.body
        return self.body
