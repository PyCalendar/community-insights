from asgiref.sync import async_to_sync

from community_insights.github import Client


def answering(*responses, sent=None):
    """A real client whose session answers with the responses, in order;
    the requests are added to `sent`."""
    client = Client("secret")
    answers = iter(responses)

    async def post(url, json, timeout):
        if sent is not None:
            sent.append((url, json))
        answer = next(answers)
        if isinstance(answer, Exception):
            raise answer
        return answer

    client.session.post = post
    return client


def run(coroutine_function, *args, **kwargs):
    """Run an async function from a test."""
    return async_to_sync(coroutine_function)(*args, **kwargs)
