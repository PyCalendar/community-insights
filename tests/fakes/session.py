import json

import httpx
import respx
from asgiref.sync import async_to_sync

from community_insights.github import Client
from community_insights.github.anonymous import AnonymousClient


def router(responses, sent=None) -> respx.MockRouter:
    """A respx router that answers every request with the next of the responses.

    Args:
        responses: httpx answers, or exceptions to raise, in order.
        sent: A list to add each request to, as the address and its JSON, or None.

    Returns:
        The router, to be the transport of a client.
    """
    answers = iter(responses)

    def answer(request: httpx.Request):
        """The next prepared answer; the request is noted."""
        if sent is not None:
            sent.append((str(request.url), json.loads(request.content or b"null")))
        found = next(answers)
        if isinstance(found, Exception):
            raise found
        return found

    mock = respx.MockRouter(assert_all_called=False)
    mock.route().mock(side_effect=answer)
    return mock


def answering(*responses, sent=None):
    """A real client whose requests are answered by respx with the responses, in order.

    Args:
        *responses: httpx answers, or exceptions to raise.
        sent: A list to add each request to, as the address and its JSON, or None.

    Returns:
        The client.
    """
    return Client("secret", transport=httpx.MockTransport(router(responses, sent).async_handler))


def answering_rest(*responses, sent=None):
    """A real client without a token whose requests are answered by respx, in order.

    Args:
        *responses: httpx answers, or exceptions to raise.
        sent: A list to add each request to, as the address and its JSON, or None.

    Returns:
        The client.
    """
    return AnonymousClient(transport=httpx.MockTransport(router(responses, sent).async_handler))


def run(coroutine_function, *args, **kwargs):
    """Run an async function from a test."""
    return async_to_sync(coroutine_function)(*args, **kwargs)
