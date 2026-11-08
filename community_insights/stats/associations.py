"""The statuses of people in a repository, as GitHub names them."""

from ..classify import MEMBERS  # collaborator or higher: who may merge, close and maintain

# the statuses in a repository, the most privileged first
ASSOCIATIONS = [
    "owner",
    "member",
    "collaborator",
    "contributor",
    "first_timer",
    "first_time_contributor",
    "mannequin",
    "none",
]
__all__ = ["ASSOCIATIONS", "MEMBERS", "more_privileged"]


def more_privileged(first: str, second: str) -> str:
    """The more privileged of two statuses in a repository.

    Args:
        first: A status such as ``member``, any case; "" for none known.
        second: Another one.

    Returns:
        The more privileged one, lowercase.

    Examples:
        >>> more_privileged("CONTRIBUTOR", "member"), more_privileged("", "none")
        ('member', 'none')
    """
    first, second = first.lower(), second.lower()

    def rank(name: str) -> int:
        return ASSOCIATIONS.index(name) if name in ASSOCIATIONS else len(ASSOCIATIONS)

    return first if rank(first) <= rank(second) else second
