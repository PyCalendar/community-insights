from dataclasses import dataclass
from datetime import datetime

from ..models import Event
from .associations import MEMBERS


@dataclass(frozen=True)
class Response:
    """One response to a pull request or an issue: what somebody else than the author did.

    A response is a comment or a review by somebody else than the author, or the merge or the
    close of the item by somebody else than the author. ``responses_to`` finds them; see
    ``docs/explanation/responses.rst``.

    Attributes:
        actor: The handle of who responded.
        association: Their status in the repository, lowercase, such as ``member``.
        is_bot: Whether GitHub marks them as a bot.
        at: When.
        seconds: The seconds from the creation of the item until then, at least 0.
        kind: ``comment``, ``review``, ``merge`` or ``close``.
        state: The state of a review, such as ``approved``; "" for the others.
    """

    MERGE, CLOSE = "merge", "close"

    actor: str
    association: str
    is_bot: bool
    at: datetime
    seconds: float
    kind: str
    state: str = ""

    @property
    def by_collaborator(self) -> bool:
        """Whether a collaborator or higher (owner, member, collaborator) responded.

        Examples:
            >>> from datetime import datetime
            >>> Response("kim", "member", False, datetime(2026, 1, 1), 0, "comment").by_collaborator
            True
        """
        return self.association in MEMBERS

    @property
    def needs_reply(self) -> bool:
        """Whether the author is expected to answer it: feedback on the page Replies.

        Comments and reviews are feedback, except a review that approves; a merge or a close
        ends the conversation.

        Examples:
            >>> from datetime import datetime
            >>> def response(kind, state=""):
            ...     return Response("kim", "member", False, datetime(2026, 1, 1), 0, kind, state)
            >>> response("comment").needs_reply, response("review", "approved").needs_reply
            (True, False)
            >>> response("merge").needs_reply
            False
        """
        if self.kind == Event.REVIEW:
            return self.state != Event.APPROVED
        return self.kind == Event.COMMENT
