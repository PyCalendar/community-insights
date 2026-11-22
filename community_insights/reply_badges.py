"""The badges of the replies of a person: their colours, their texts, and an example of each."""

from .badge_spec import BadgeSpec
from .stats.contributor_replies import GREEN, RED, YELLOW, ContributorReplies

COLORS = {GREEN: "#2da44e", YELLOW: "#bf8700", RED: "#cf222e"}
NO_FEEDBACK = "#9f9f9f"  # grey: the person has no pull request that counts


def reply_spec(login: str, person: ContributorReplies | None, data=None) -> BadgeSpec:
    """The badge of the replies of a person.

    Args:
        login: The handle of the person.
        person: Their replies; None if they have no pull request that counts.
        data: The data of the JSON besides the badge.

    Returns:
        The spec: green, yellow or red, or grey without feedback. The texts are in English,
        as the badges in READMEs.

    Examples:
        >>> reply_spec("kim", None).message
        'no feedback yet'
        >>> reply_spec("kim", ContributorReplies("kim", prs=2, with_feedback=2)).message
        '2/2 PRs answered'
        >>> reply_spec("kim", ContributorReplies("kim", prs=1, with_feedback=1,
        ...                                       unanswered={"o/r": [7]})).message
        '0/1 PRs answered'
    """
    if person is None:
        return BadgeSpec(login, "no feedback yet", NO_FEEDBACK, data or {})
    # answered of those that count, as on the page: "1/1 PRs answered" is all of them
    message = f"{person.answered}/{person.with_feedback} PRs answered"
    return BadgeSpec(login, message, COLORS[person.status], data or {})


# one badge of each kind, for the documentation (manage.py reply_badge_examples)
EXAMPLES = {
    "green": ContributorReplies("kim", prs=3, with_feedback=3),
    "yellow": ContributorReplies("kim", prs=1, with_feedback=1, unanswered={"o/r": [7]}),
    "red": ContributorReplies(
        "kim", prs=4, with_feedback=3, unanswered={"o/r": [7, 9]}, closed={("o/r", 9)}
    ),
    "grey": None,
}
