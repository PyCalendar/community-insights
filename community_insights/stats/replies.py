"""Whether the authors of pull requests answered the comments and reviews they got."""

from collections import defaultdict
from datetime import datetime
from fractions import Fraction

from ..models import Event, Item, ItemCommit
from .contributor_replies import GREEN, RED, YELLOW, ContributorReplies
from .pull_reply import PullReply
from .selection import items_in

# what the table of replies can be sorted by, each with the worst first
SORT_KEYS = {
    "open": lambda p: -sum(len(n) for n in p.unanswered_open.values()),
    "replied": lambda p: (Fraction(p.answered, p.with_feedback), -p.with_feedback),
    "badge": lambda p: {RED: 0, YELLOW: 1, GREEN: 2}[p.status],
    "closed": lambda p: -sum(len(n) for n in p.unanswered_closed.values()),
    "merged": lambda p: (Fraction(p.merged, p.total or 1), -p.total),
    "person": lambda p: p.login.lower(),
}
DEFAULT_ORDER = ["open", "replied", "person", "badge", "closed", "merged"]


def sort_order(wanted) -> list[str]:
    """The keys to sort the table by: the wanted ones first, then the others by default.

    Args:
        wanted: Keys of ``SORT_KEYS``, such as ``["badge", "person"]``; unknown ones and
            repeated ones are left out.

    Returns:
        All keys, each once.

    Examples:
        >>> sort_order(["merged", "nonsense", "merged", "person"])
        ['merged', 'person', 'open', 'replied', 'badge', 'closed']
        >>> sort_order([]) == DEFAULT_ORDER
        True
    """
    found = [key for key in dict.fromkeys(wanted) if key in SORT_KEYS]
    return found + [key for key in DEFAULT_ORDER if key not in found]


def order(person: ContributorReplies, keys: list[str] | None = None) -> tuple:
    """The place of a person in the list, by the keys in their order.

    By default an open pull request without reply first (more of them first), then the
    smallest share of replies: replied to/that count, so 0/5 and 0/1 come before 1/2; with
    the same share, more pull requests that count first: 0/5 before 0/1; then by the handle.

    Args:
        person: The replies of the person.
        keys: The keys of ``SORT_KEYS`` in their order; None for ``DEFAULT_ORDER``.

    Returns:
        The key to sort by.

    Examples:
        >>> people = [
        ...     ContributorReplies("a", with_feedback=2, unanswered={"o/r": [1]}, total=2),
        ...     ContributorReplies("b", with_feedback=1, unanswered={"o/r": [2]}, total=1),
        ...     ContributorReplies(
        ...         "c", with_feedback=5, unanswered={"o/r": [3, 4, 5, 6, 7]}, total=5
        ...     ),
        ...     ContributorReplies("d", with_feedback=3, total=3),
        ...     ContributorReplies(
        ...         "e", with_feedback=1, unanswered={"o/r": [8]}, closed={("o/r", 8)}, total=1
        ...     ),
        ... ]
        >>> [p.login for p in sorted(people, key=order)]
        ['c', 'b', 'a', 'e', 'd']
        >>> [p.login for p in sorted(people, key=lambda p: order(p, ["person"]))]
        ['a', 'b', 'c', 'd', 'e']
    """
    return tuple(SORT_KEYS[key](person) for key in (keys or DEFAULT_ORDER))


def answered(author: str, feedback: list[datetime], own: list[datetime]) -> bool | None:
    """Whether the author answered: did something after the first feedback.

    Args:
        author: The login of the author.
        feedback: When others commented or reviewed.
        own: When the author commented, reviewed or committed.

    Returns:
        None without feedback; otherwise whether something of the author came after the first.

    Examples:
        >>> from datetime import datetime as d
        >>> answered("kim", [], [d(2026, 1, 2)]) is None
        True
        >>> answered("kim", [d(2026, 1, 2), d(2026, 1, 1)], [d(2026, 1, 1, 12)])
        True
        >>> answered("kim", [d(2026, 1, 2)], [d(2026, 1, 1)])
        False
    """
    if not feedback:
        return None
    first = min(feedback)
    return any(at > first for at in own)


def pull_replies(
    repositories,
    classifier=None,
    since: datetime | None = None,
    until: datetime | None = None,
    login: str | None = None,
) -> list[PullReply]:
    """The pull requests and whether their authors answered the feedback on them.

    Feedback is a comment or review by somebody else than the author and not by a bot: not
    marked as a bot by GitHub, and not of the class of bots of the classifier; an approving
    review is no feedback either: it needs no reply. The author
    answers with a comment, a review or a commit after the first feedback. Pull requests
    opened by bots are left out.

    Args:
        repositories: The repositories.
        classifier: Decides which accounts are bots; None for those GitHub marks.
        since: The start of the time range of the pull requests, None for the beginning.
        until: Its end, excluded; None for now.
        login: Only this author, in any case; None for everybody.

    Returns:
        The pull requests, also the merged ones, by repository and number.
    """
    from ..tables.items import bot_logins

    bots = bot_logins(repositories, classifier) if classifier is not None else set()
    items = items_in(repositories, since, until).filter(kind=Item.PR, author_is_bot=False)
    items = items.exclude(author="")
    if login:
        items = items.filter(author__iexact=login)
    rows = list(
        items.values_list(
            "pk",
            "author",
            "repository__full_name",
            "number",
            "title",
            "state",
            "merged",
            "closed_by",
            "created_at",
        ).order_by("repository__full_name", "number")
    )
    ids = [row[0] for row in rows]
    events: dict[int, list] = defaultdict(list)
    for item, actor, is_bot, at, kind, state in (
        Event.objects.filter(item__in=ids)
        .exclude(kind=Event.OPENED)
        .values_list("item", "actor", "is_bot", "at", "kind", "state")
    ):
        approval = kind == Event.REVIEW and state == Event.APPROVED
        events[item].append((actor.lower(), is_bot, at, approval))
    commits: dict[int, list] = defaultdict(list)
    for item, actor, at in ItemCommit.objects.filter(item__in=ids).values_list(
        "item", "actor", "at"
    ):
        commits[item].append((actor.lower(), at))
    found = []
    for pk, author, repository, number, title, state, merged, closed_by, created in rows:
        key = author.lower()
        feedback = [  # an approval is no feedback to reply to
            at
            for actor, is_bot, at, approval in events[pk]
            if actor != key and not is_bot and actor not in bots and not approval
        ]
        own = [at for actor, _, at, _ in events[pk] if actor == key]
        own += [at for actor, at in commits[pk] if actor == key]
        found.append(
            PullReply(
                author=author,
                repository=repository,
                number=number,
                title=title,
                state=state,
                merged=merged,
                closed_by=closed_by,
                created_at=created,
                first_feedback=min(feedback) if feedback else None,
                answered=answered(key, feedback, own),
            )
        )
    return found


def replies(
    repositories,
    classifier=None,
    since: datetime | None = None,
    until: datetime | None = None,
    login: str | None = None,
) -> list[ContributorReplies]:
    """The authors of pull requests who got feedback, and whether they answered it.

    Merged pull requests need no answer and are only counted (``merged``); those the author
    closed without merging are left out. The others count: the open ones and those somebody
    else closed without merging. See ``pull_replies``.

    Args:
        repositories: The repositories.
        classifier: Decides which accounts are bots; None for those GitHub marks.
        since: The start of the time range of the pull requests, None for the beginning.
        until: Its end, excluded; None for now.
        login: Only this author, in any case; None for everybody.

    Returns:
        The authors with feedback on a pull request that was not merged, in their order
        (see ``order``).
    """
    return replies_of(pull_replies(repositories, classifier, since, until, login))


def replies_of(pulls: list[PullReply], keys: list[str] | None = None) -> list[ContributorReplies]:
    """The authors of the pull requests who got feedback, and whether they answered it.

    Args:
        pulls: The pull requests, from ``pull_replies``.
        keys: What to sort by (see ``order``); None for ``DEFAULT_ORDER``.

    Returns:
        The authors with a pull request that counts, in their order.
    """
    people: dict[str, ContributorReplies] = {}
    for pull in pulls:
        person = people.setdefault(pull.author.lower(), ContributorReplies(pull.author))
        person.total += 1
        if pull.merged:
            person.merged += 1
            continue
        if pull.closed_by_author:  # given up by the author: nothing to answer any more
            continue
        person.prs += 1
        if pull.closed_by_others:
            person.closed_by_others += 1
        if pull.answered is None:
            continue
        person.with_feedback += 1
        if not pull.answered:
            person.unanswered.setdefault(pull.repository, []).append(pull.number)
            if pull.state == "closed":
                person.closed.add((pull.repository, pull.number))
    return sorted((p for p in people.values() if p.with_feedback), key=lambda p: order(p, keys))


def pull_order(pull: PullReply) -> tuple:
    """The place of a pull request on the page of a person: those without reply first.

    Open ones without reply, then closed ones without reply, then the answered ones, those
    without feedback, and those that do not count (merged or closed by the author); the newest
    first in each.

    Args:
        pull: The pull request.

    Returns:
        The key to sort by.
    """
    if pull.unanswered:
        group = 0 if pull.state == "open" else 1
    elif not pull.counted:
        group = 4
    else:
        group = 2 if pull.answered else 3
    return (group, -pull.created_at.timestamp())


def commits_unread(repositories) -> int:
    """The pull requests read before their commits were read: a fetch reads them again.

    Without their commits, an answer by a commit is not seen.

    Args:
        repositories: The repositories.

    Returns:
        How many.
    """
    return Item.objects.filter(
        repository__in=repositories, kind=Item.PR, details__lt=Item.DETAILS
    ).count()
