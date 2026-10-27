import math

from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.cache import never_cache

from .. import badges, stats
from ..classify import Classifier, class_list, classes_by_ids
from ..errors import UnknownClasses
from ..models import Item, Project
from .scope import PROJECTS, public_repositories

LABEL_LENGTH = 60  # the longest left side of a badge


def badge_of(request, repositories, user) -> HttpResponse:
    """A badge of the response time of the repositories, from the database.

    Args:
        request: Its parameters: kind (pr, issue), percentile (0-100), class, classes (the
            ids of the classes of a shared address), model
            (measured, normal, exponential, kaplan-meier), label (the text of the left side
            instead of the one made from the others).
        repositories: The repositories.
        user: Whose classes of people count; None for the default ones.

    Returns:
        The SVG, cached by browsers and proxies for 15 minutes.

    Raises:
        Http404: If the class or the model does not exist.
    """
    kind = Item.ISSUE if request.GET.get("kind") == "issue" else Item.PR
    try:
        p = float(request.GET.get("percentile", 50))
    except ValueError:
        p = 50.0
    p = 50.0 if math.isnan(p) else min(max(p, 0.0), 100.0)
    wanted = request.GET.get("class", "")
    try:  # the classes of a shared address, or those of the user
        chosen = classes_by_ids(request.GET.get("classes", "")) or None
    except UnknownClasses:
        raise Http404("No such classes") from None
    names = {c.name for c in chosen} if chosen else {c.name for c in class_list(user)}
    if wanted and wanted not in names:
        raise Http404("No such class")
    model = request.GET.get("model") or "measured"
    if model not in stats.MODELS:
        raise Http404("No such model")
    repositories.update(last_used_at=timezone.now())
    entries, observed = stats.response_times(repositories.all(), Classifier(user, chosen=chosen))
    seconds, counted = stats.model_percentile(
        entries[kind], observed[kind], wanted or None, p, model
    )
    label = f"{'PR' if kind == Item.PR else 'issue'} response p{p:g}"
    details = [part for part in (wanted, "" if model == "measured" else model) if part]
    if details:
        label += f" ({', '.join(details)})"
    custom = " ".join(request.GET.get("label", "").split())[:LABEL_LENGTH]
    if custom:  # the left side, chosen by the people who embed the badge
        label = custom
    if seconds is not None:
        value = stats.format_duration(seconds)
    else:  # Kaplan-Meier: that share never got a response
        value = "not reached" if counted and model == "kaplan-meier" else "no data"
    response = HttpResponse(
        badges.badge(label, value, "#2a7de1" if seconds is not None else "#9f9f9f"),
        content_type="image/svg+xml",
    )
    response["Cache-Control"] = "public, max-age=900"
    return response


@never_cache
def badge(request, token):
    """The badge of a project: the secret token is the access. Never calls GitHub.

    Args:
        request: The request, with the parameters of the badge.
        token: The secret token of the project.

    Returns:
        The SVG.
    """
    project = get_object_or_404(Project, badge_token=token)
    return badge_of(request, project.repositories, project.user)


@never_cache
def public_badge(request, scope):
    """The badge of public repositories, with the default classes. Never calls GitHub.

    Args:
        request: The request, with the parameters of the badge.
        scope: The text of a public scope.

    Returns:
        The SVG.

    Raises:
        Http404: If the scope is no public one or none of it is known.
    """
    if PROJECTS.match(scope):
        raise Http404("Projects have badges with their secret token")
    return badge_of(request, public_repositories(scope), None)
