"""How often visitors without an account may add repositories and fetch: per address and hour.

Visitors use the tokens people donated to the site. A limit per address keeps one visitor from
using them all up. django-ratelimit counts; the address comes from ``client_address``, which
trusts only the proxies of ``TRUSTED_PROXIES``.
"""

from django.conf import settings
from django.utils.translation import gettext
from django_ratelimit.core import is_ratelimited

from .errors import VisitorLimitReached


def client_address(request, proxies: int | None = None) -> str:
    """The address of the visitor, behind the trusted proxies.

    Each proxy adds the address it was reached from to ``X-Forwarded-For``. With ``proxies``
    trusted proxies in front of Django (``TRUSTED_PROXIES``, 1 for the nginx of the container),
    the visitor is the address that the outermost one added. Addresses added before it can be
    made up by the visitor, so they are not used.

    Args:
        request: The request.
        proxies: How many proxies to trust, ``TRUSTED_PROXIES`` if None.

    Returns:
        The address.

    Examples:
        >>> from django.test import RequestFactory
        >>> request = RequestFactory().get("/", REMOTE_ADDR="127.0.0.1",
        ...                                HTTP_X_FORWARDED_FOR="6.6.6.6, 203.0.113.9")
        >>> client_address(request, 0), client_address(request, 1), client_address(request, 5)
        ('127.0.0.1', '203.0.113.9', '6.6.6.6')
    """
    trusted: int = settings.TRUSTED_PROXIES if proxies is None else proxies
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    chain = [part.strip() for part in forwarded.split(",") if part.strip()]
    chain.append(request.META.get("REMOTE_ADDR", ""))
    return chain[max(0, len(chain) - 1 - trusted)]


class VisitorLimit:
    """A number of actions per hour for each address of visitors without an account.

    Args:
        action: The name of the action, such as ``submit``.
        per_hour: How many are allowed per hour; 0 for no limit.
    """

    def __init__(self, action: str, per_hour: int):
        """Count actions of visitors per address and hour.

        Args:
            action: The name of the action, such as ``submit``.
            per_hour: How many are allowed per hour; 0 for no limit.
        """
        self.action = action
        self.per_hour = per_hour

    def count(self, request) -> None:
        """Count an action of a visitor; people with an account are not limited.

        django-ratelimit counts in the cache, per action and address, in windows of an hour.

        Args:
            request: The request of the action.

        Raises:
            VisitorLimitReached: If the address did this too often in this hour.
        """
        if self.per_hour <= 0 or request.user.is_authenticated:
            return
        if is_ratelimited(
            request,
            group=f"visitor-limit:{self.action}",
            key=lambda group, request: client_address(request),
            rate=f"{self.per_hour}/h",
            increment=True,
        ):
            raise VisitorLimitReached(
                gettext(
                    "Visitors may do this %(times)s times per hour. "
                    "Sign up to use your own tokens, or wait for the next hour."
                )
                % {"times": self.per_hour}
            )
