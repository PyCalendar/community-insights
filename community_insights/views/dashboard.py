from allauth.socialaccount.models import SocialAccount
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from .. import pipeline, stats
from ..classify import Classifier, ensure_default_classes
from ..feedback import show_error
from ..models import (
    AccessToken,
    Item,
    Profile,
    Project,
    Repository,
)
from ..sync import add_project
from ..tokens import ask


def add_project_for(user, target: str):
    """Add a repository or organisation with the tokens of the user.

    Add a repository or organisation with the tokens of the user, or without a token if there is
    none.
    """
    from asgiref.sync import async_to_sync, sync_to_async

    from ..github.anonymous import AnonymousClient
    from ..tokens import TokenPool, entries_for

    async def adding():
        entries = await sync_to_async(entries_for)(user)
        reader = TokenPool(entries) if entries else AnonymousClient()
        try:
            return await add_project(user, reader, target)
        finally:
            await reader.close()

    return async_to_sync(adding)()


def github_login(user) -> str:
    """The GitHub login of a user: of the linked account, else of the first token."""
    account = SocialAccount.objects.filter(user=user, provider="github").first()
    if account:
        return account.extra_data.get("login", "")
    token = AccessToken.objects.filter(user=user).first()
    return token.login if token else ""


def refresh_suggestions(user) -> None:
    """Load the repositories and organisations to offer from GitHub."""
    found = ask(user, "suggestions")
    profile = Profile.of(user)
    profile.suggestions = found
    profile.suggestions_fetched_at = timezone.now()
    profile.save()


def source_choices(user) -> list[dict]:
    """For the source picker: the projects first, then the suggestions.

    Visitors get the public repositories the site knows, most stars first.

    Returns:
        Choices with "name", "kind" and "stars".
    """
    if not user.is_authenticated:
        known = Repository.objects.filter(is_private=False).order_by("-stars")[:200]
        return [{"name": r.full_name, "kind": "known", "stars": r.stars} for r in known]
    profile = Profile.of(user)
    projects = list(user.projects.all())
    have = {p.target.lower() for p in projects}
    choices = [{"name": p.target, "kind": "project", "stars": 0, "id": p.pk} for p in projects]
    choices += [s for s in profile.suggestions if s["name"].lower() not in have]
    return choices


def numbers_of(user, repositories) -> dict:
    """The few numbers of a card, from the database.

    Args:
        user: Whose classes of people count; visitors get the default ones.
        repositories: The repositories of the card.

    Returns:
        How many repositories, the counts, the median first response and how
        complete the data is.
    """
    entries = stats.response_entries(repositories, Classifier(user))
    seconds, _ = stats.class_percentile(entries[Item.PR] + entries[Item.ISSUE], None, 50)
    return {
        "repositories": repositories.count(),
        "counts": stats.counts(repositories),
        "median": seconds,
        "data": pipeline.completeness(repositories),
    }


def project_card(user, project: Project) -> dict:
    """The card of a project on the dashboard."""
    return {"project": project, **numbers_of(user, project.repositories.all())}


@login_required
def dashboard(request):
    """The dashboard: the projects as cards, and adding repositories."""
    user = request.user
    ensure_default_classes(user)
    login = github_login(user)
    if request.method == "POST":
        try:
            if "refresh" in request.POST:
                refresh_suggestions(user)
                messages.success(request, _("The suggestions were read from GitHub."))
            else:
                project = add_project_for(user, request.POST.get("target", ""))
                messages.success(request, _("%(target)s was added.") % {"target": project.target})
        except Exception as error:  # shown with what to do
            show_error(request, error)
        return redirect("dashboard")
    return render(
        request,
        "community/dashboard.html",
        {
            "cards": [project_card(user, p) for p in user.projects.all()],
            "projects": user.projects.all(),
            "choices": source_choices(user),
            "profile": Profile.of(user),
            "login": login,
        },
    )


@login_required
@require_POST
def project_delete(request, pk):
    """Remove a project; its data stays until the cache is cleaned."""
    get_object_or_404(Project, pk=pk, user=request.user).delete()
    return redirect("dashboard")


@login_required
@require_POST
def project_rename(request, pk):
    """Show the project with a name; an empty name shows its owner/name again."""
    project = get_object_or_404(Project, pk=pk, user=request.user)
    project.name = request.POST.get("name", "").strip()[:100]
    project.save(update_fields=["name"])
    messages.success(
        request,
        _("%(target)s is shown as %(label)s.") % {"target": project.target, "label": project.label},
    )
    return redirect("dashboard")
