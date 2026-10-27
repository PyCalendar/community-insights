"""How many pull requests and issues the projects of an account may hold (``USER_MAX_ITEMS``).

The administrators have no limit. Visitors have their own limits (``visitor_limit``).
"""

from django.conf import settings
from django.utils.translation import gettext

from .errors import UserItemsLimitReached
from .models import Item


def limit_of(user) -> int | None:
    """The most pull requests and issues the projects of a user may hold.

    Args:
        user: The user.

    Returns:
        The number, None for no limit: for administrators, or ``USER_MAX_ITEMS`` of 0.
    """
    if user.is_staff or not settings.USER_MAX_ITEMS:
        return None
    return settings.USER_MAX_ITEMS


def items_of(user) -> int:
    """The pull requests and issues the repositories of the projects of a user hold.

    Args:
        user: The user.

    Returns:
        The number; an item of a repository in several projects counts once.
    """
    return Item.objects.filter(repository__projects__user=user).distinct().count()


def check(user, adding: int) -> None:
    """Check that a fetch keeps the projects of a user within the limit.

    Args:
        user: The user who fetches.
        adding: The pull requests and issues the fetch adds.

    Raises:
        UserItemsLimitReached: If the projects would hold more than the limit.
    """
    limit = limit_of(user)
    if limit is None:
        return
    held = items_of(user)
    if held + adding > limit:
        raise UserItemsLimitReached(
            gettext(
                "Your projects hold %(held)s pull requests and issues; this fetch adds about "
                "%(adding)s, and %(limit)s are allowed."
            )
            % {"held": held, "adding": adding, "limit": limit}
        )
