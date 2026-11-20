"""Open drafts do not count as open pull requests, unless the page says so (``drafts=1``)."""

import pytest

from community_insights import stats
from community_insights.models import Item, Repository
from community_insights.views.scope import drafts_of

pytestmark = pytest.mark.django_db


def waiting(replied) -> stats.PullReply:
    """An open pull request with feedback its author did not answer, made a draft.

    Args:
        replied: The repository with replies.

    Returns:
        The pull request.
    """
    pulls = stats.pull_replies(Repository.objects.all())
    found = next(p for p in pulls if p.state == "open" and p.first_feedback and not p.answered)
    Item.objects.filter(kind=Item.PR, number=found.number).update(draft=True)
    return found


def test_open_drafts_are_left_out_of_the_replies(replied):
    """The author of a draft is not done yet and need not answer."""
    draft = waiting(replied)
    numbers = {p.number for p in stats.pull_replies(Repository.objects.all())}
    assert draft.number not in numbers
    with_drafts = stats.pull_replies(Repository.objects.all(), drafts=True)
    assert draft.number in {p.number for p in with_drafts}


def test_the_replies_of_a_person_with_and_without_drafts(replied):
    """The unanswered open pull requests of the author change with the choice."""
    draft = waiting(replied)
    login = draft.author

    def unanswered(drafts):
        """The open pull requests of the author without an answer."""
        found = stats.replies(Repository.objects.all(), login=login, drafts=drafts)
        return sum(len(n) for n in found[0].unanswered_open.values()) if found else 0

    assert unanswered(True) == unanswered(False) + 1


def test_closed_drafts_count_as_closed(replied):
    """Only open drafts are left out: one closed while a draft stays."""
    closed = Item.objects.filter(kind=Item.PR, state="closed").first()
    Item.objects.filter(pk=closed.pk).update(draft=True)
    assert closed.number in {p.number for p in stats.pull_replies(Repository.objects.all())}


def test_open_drafts_are_not_open_pull_requests_of_a_contributor(replied):
    """prs_open leaves them out by default; prs_draft counts them either way."""
    draft = waiting(replied)

    def person(drafts):
        """The author as a contributor."""
        found = stats.contributors(Repository.objects.all(), drafts=drafts)
        return next(c for c in found if c.login.lower() == draft.author.lower())

    without, including = person(False), person(True)
    assert including.prs_open == without.prs_open + 1
    assert without.prs_draft == including.prs_draft == 1


@pytest.mark.parametrize(
    ("value", "counts"),
    [("1", True), ("on", True), ("true", True), ("0", False), ("", False), ("no", False)],
)
def test_the_parameter(value, counts):
    """drafts=1 and the values of a checkbox count them."""
    assert drafts_of({"drafts": value}) is counts
