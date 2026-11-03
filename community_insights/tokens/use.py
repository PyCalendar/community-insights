from typing import NamedTuple


class Use(NamedTuple):
    """What a fetch for somebody else than the owner of the tokens is for.

    The grants of tokens (``TokenGrant``) that cover it let it use their points.

    Attributes:
        kind: ``TokenGrant.BADGES``, ``PAGES`` or ``VISITORS``.
        scope: The public scope, such as ``collective~icalendar`` or ``collective``.
        login: The person of a badge; "" for others.
    """

    kind: str
    scope: str = ""
    login: str = ""
