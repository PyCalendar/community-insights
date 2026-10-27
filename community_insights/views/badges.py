from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.cache import never_cache

from .. import badges, stats
from ..classify import Classifier, class_list
from ..models import Item, Project
from .scope import PROJECTS, public_repositories


def badge_of(request, repositories, user) -> HttpResponse:
    """A badge of the response time of the repositories, from the database.

    Args:
        request: Its parameters: kind (pr, issue), percentile (0-100), class.
        repositories: The repositories.
        user: Whose classes of people count; None for the default ones.

    Returns:
        The SVG, cached by browsers and proxies for 15 minutes.

    Raises:
        Http404: If the class does not exist.
    """
    kind = Item.ISSUE if request.GET.get("kind") == "issue" else Item.PR
    try:
        p = min(max(float(request.GET.get("percentile", 50)), 0), 100)
    except ValueError:
        p = 50
    wanted = request.GET.get("class", "")
    if wanted and wanted not in {c.name for c in class_list(user)}:
        raise Http404("No such class")
    repositories.update(last_used_at=timezone.now())
    entries = stats.response_entries(repositories.all(), Classifier(user))[kind]
    seconds, _ = stats.class_percentile(entries, wanted or None, p)
    label = f"{'PR' if kind == Item.PR else 'issue'} response p{p:g}"
    if wanted:
        label += f" ({wanted})"
    value = stats.format_duration(seconds) if seconds is not None else "no data"
    response = HttpResponse(
        badges.badge(label, value, "#2a7de1" if seconds is not None else "#9f9f9f"),
        content_type="image/svg+xml",
    )
    response["Cache-Control"] = "public, max-age=900"
    return response


@never_cache
def badge(request, token):
    """The badge of a project: the secret token is the access. Never calls GitHub."""
    project = get_object_or_404(Project, badge_token=token)
    return badge_of(request, project.repositories, project.user)


@never_cache
def public_badge(request, scope):
    """The badge of public repositories, with the default classes. Never calls GitHub.

    Raises:
        Http404: If the scope is no public one or none of it is known.
    """
    if PROJECTS.match(scope):
        raise Http404("Projects have badges with their secret token")
    return badge_of(request, public_repositories(scope), None)
