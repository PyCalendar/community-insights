import json

import httpx


def Response(status=200, body=None, headers=None, text=""):  # noqa: N802 - reads like the class
    """An answer of GitHub, as httpx gives it, to test the real clients with respx.

    Args:
        status: The status code.
        body: The JSON of the answer; an exception for an answer that is no JSON.
        headers: The headers.
        text: The text of an answer without JSON.

    Returns:
        The answer.
    """
    if isinstance(body, Exception):
        content = str(body).encode()
    elif text and body is None:
        content = text.encode()
    else:
        content = json.dumps(body if body is not None else {}).encode()
    return httpx.Response(status, content=content, headers=headers or {})
