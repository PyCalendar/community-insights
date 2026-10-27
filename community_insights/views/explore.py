"""Explore: the public repositories the site knows, for everybody."""

from asgiref.sync import async_to_sync, sync_to_async
from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Case, When
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from ..demo import DEMO
from ..feedback import show_error
from ..github.anonymous import AnonymousClient
from ..models import Repository
from ..sync import add_public
from ..tokens import TokenPool, entries_for
from ..visitor_limit import VisitorLimit
from .dashboard import numbers_of
from .scope import scope_text

PAGE = 24


def explore(request):
    """The public repositories the site knows, as cards, and submitting more.

    Returns:
        The page, the repositories with data first, most stars first.

    Args:
        request: The request, with the search ``q`` and the ``page``.
    """
    found = Repository.objects.filter(is_private=False)
    real = found.exclude(full_name=DEMO)
    if real.exists():  # the made up demo only while there is nothing else to explore
        found = real
    search = request.GET.get("q", "").strip()
    if search:
        found = found.filter(full_name__icontains=search)
    without_data = Case(When(prs_synced_until__isnull=True, then=1), default=0)
    found = found.order_by(without_data, "-stars", "full_name")
    page = Paginator(found, PAGE).get_page(request.GET.get("page"))
    cards = [
        {
            "repository": r,
            "scope": scope_text([r]),
            **numbers_of(request.user, Repository.objects.filter(pk=r.pk)),
        }
        for r in page
    ]
    return render(request, "community/explore.html", {"page": page, "cards": cards, "q": search})


def submit_public(target: str) -> list[Repository]:
    """Check and store submitted public repositories with the donated tokens.

    Without donated tokens, GitHub is asked without a token.

    Returns:
        The stored repositories.

    Args:
        target: ``owner/name`` or ``owner``, as typed or pasted.
    """

    async def submitting():
        entries = await sync_to_async(entries_for)(None)
        reader = TokenPool(entries) if entries else AnonymousClient()
        try:
            return await add_public(reader, target)
        finally:
            await reader.close()

    return async_to_sync(submitting)()


@require_POST
def submit(request):
    """Add a public repository or organisation and show its statistics page.

    Args:
        request: The request, with ``target``.

    Returns:
        A redirect to the statistics, or back to Explore with the error.
    """
    target = request.POST.get("target", "")
    try:
        VisitorLimit("submit", settings.VISITOR_SUBMITS_PER_HOUR).count(request)
        repositories = submit_public(target)
    except Exception as error:  # shown with what to do
        show_error(request, error)
        return redirect("explore")
    text = scope_text(repositories) if "/" in target.strip("/ ") else repositories[0].owner_login
    return redirect("overview", scope=text)
