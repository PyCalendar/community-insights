"""The translation table: any exception becomes an error people understand."""

import niquests
import requests

from .base import CommunityError, UnexpectedError
from .github import GitHubError, GitHubUnreachable
from .input import InvalidInput


def all_errors() -> dict[str, type[CommunityError]]:
    """Every error class by its name.

    Returns:
        The classes by their names.
    """
    found, todo = {}, [CommunityError]
    while todo:
        cls = todo.pop()
        found[cls.__name__] = cls
        todo.extend(cls.__subclasses__())
    return found


def by_code(code: str) -> type[CommunityError] | None:
    """The class of an error by its name, as stored with jobs and tokens; None if unknown.

    Args:
        code: The name of the class.

    Returns:
        The class.
    """
    return all_errors().get(code or "")


def translate(error: BaseException) -> CommunityError:
    """The error to show for any exception: the translation table.

    Args:
        error: Any exception.

    Returns:
        The error of errors/: the same one, the one it means, or ``UnexpectedError``.
    """
    if isinstance(error, CommunityError):
        return error
    unreachable = (
        requests.Timeout,
        requests.ConnectionError,
        niquests.Timeout,
        niquests.ConnectionError,
    )
    if isinstance(error, unreachable):
        return GitHubUnreachable(str(error))
    if isinstance(error, requests.RequestException | niquests.RequestException):
        return GitHubError(str(error))
    if isinstance(error, ValueError):
        return InvalidInput(str(error))
    return UnexpectedError(f"{type(error).__name__}: {error}")
