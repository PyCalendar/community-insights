"""The pages and badges of code suggestions: were they applied to the pull requests?"""

from django.conf import settings
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse

from .. import pipeline, stats
from ..badge_spec import BadgeSpec
from ..models import Item, Project, TokenGrant
from ..reply_badges import COLORS, NO_FEEDBACK
from ..stats.suggestion_summary import GREY, SuggestionSummary
from ..sync.suggestions import STATUSES
from ..tokens.use import Use
from .replies import BADGE_KEPT, public_badge_scope
from .scope import PROJECTS, Scope, public_repositories, scope_of, scope_view, stats_page

PULLS_PER_PAGE = 25  # pull requests with their suggestions on a page


def statuses_of(request) -> list[str]:
    """The statuses the filter shows: all by default; those checked after the form was sent.

    Args:
        request: The request: ``status`` for each status checked, ``filtered`` when the form
            was sent, so that none checked shows none.

    Returns:
        The statuses, in the order of the pages.
    """
    if not request.GET.get("filtered"):
        return list(STATUSES)
    checked = request.GET.getlist("status")
    return [status for status in STATUSES if status in checked]


def repository_of(text: str) -> str:
    """The full name of a repository of an address: ``owner~name`` is ``owner/name``.

    Args:
        text: The part of the address.

    Returns:
        The full name.

    Examples:
        >>> repository_of("collective~icalendar")
        'collective/icalendar'
    """
    return text.replace("~", "/")


def suggestions_page(request, scope: Scope, template: str, context: dict, **filters):
    """A page of suggestions grouped by pull request, filtered by status, in pages.

    Args:
        request: The request.
        scope: The scope.
        template: The template.
        context: What else the template needs.
        **filters: ``author`` or ``pull`` for ``stats.pull_suggestions``.

    Returns:
        The page.
    """
    statuses = statuses_of(request)
    groups = stats.pull_suggestions(
        scope.repositories, scope.since, scope.until, statuses=statuses, **filters
    )
    page = Paginator(groups, PULLS_PER_PAGE).get_page(request.GET.get("page"))
    summary = SuggestionSummary.of(
        s.status
        for group in stats.pull_suggestions(scope.repositories, scope.since, scope.until, **filters)
        for s in group.suggestions
    )
    return stats_page(
        request,
        scope,
        template,
        {
            **context,
            "scope": scope,
            "page": page,
            "summary": summary,
            "statuses": statuses,
            "all_statuses": STATUSES,
            "reads_threads": True,
        },
    )


@scope_view
def suggestions(request, scope):
    """The suggestions of all pull requests of a scope, grouped by pull request.

    Args:
        request: The request.
        scope: The text of the scope.

    Returns:
        The page.
    """
    scope = scope_of(request, scope)
    return suggestions_page(request, scope, "community/suggestions.html", {})


@scope_view
def person_suggestions(request, scope, login):
    """The suggestions on the pull requests of a person, grouped by pull request.

    Args:
        request: The request.
        scope: The text of the scope.
        login: The author of the pull requests.

    Returns:
        The page.
    """
    scope = scope_of(request, scope)
    return suggestions_page(
        request,
        scope,
        "community/person_suggestions.html",
        {"login": login, "badge": suggestion_badge_path(scope, login=login)},
        author=login,
    )


@scope_view
def pull_suggestions(request, scope, repository, number):
    """The suggestions of one pull request.

    Args:
        request: The request.
        scope: The text of the scope.
        repository: The repository as ``owner~name``.
        number: The number of the pull request.

    Returns:
        The page.

    Raises:
        Http404: If the scope has no such pull request.
    """
    scope = scope_of(request, scope)
    name = repository_of(repository)
    item = Item.objects.filter(
        repository__in=scope.repositories,
        repository__full_name=name,
        kind=Item.PR,
        number=number,
    ).first()
    if item is None:
        raise Http404("No such pull request")
    return suggestions_page(
        request,
        scope,
        "community/pull_suggestions.html",
        {
            "item": item,
            "badge": suggestion_badge_path(scope, pull=(repository, number)),
            "pull_summary": stats.summarize_suggestions(scope.repositories, pull=(name, number)),
        },
        pull=(name, number),
    )


def suggestion_badge_path(
    scope: Scope, login: str | None = None, pull: tuple[str, int] | None = None, extension="svg"
) -> str | None:
    """The address of the badge of suggestions of a person or of a pull request.

    Public repositories have it by their names; one project by its secret token.

    Args:
        scope: The scope of the page.
        login: The author of the pull requests.
        pull: The repository as ``owner~name`` and the number of a pull request.
        extension: ``svg``, ``png`` or ``json``.

    Returns:
        The path; None if the scope has neither one project nor public repositories.
    """
    public = public_badge_scope(scope)
    if public:
        if pull:
            return reverse("public_pull_suggestion_badge", args=[public, *pull, extension])
        return reverse("public_suggestion_badge", args=[public, login, extension])
    if not scope.public and len(scope.projects) == 1:
        token = scope.projects[0].badge_token
        if pull:
            return reverse("pull_suggestion_badge", args=[token, *pull, extension])
        return reverse("suggestion_badge", args=[token, login, extension])
    return None


def suggestion_badge_of(
    repositories, user, label: str, summary_of, reason_url: str, use=None, extension="svg"
) -> HttpResponse:
    """A badge of suggestions, after fetching what changed.

    Args:
        repositories: The repositories.
        user: Whose tokens fetch; None for the shared ones.
        label: The left side, such as the login or ``PR #12``.
        summary_of: Makes the summary after the fetch.
        reason_url: The address of the badge, for the page Downloads.
        use: The public use of the badge (``tokens.Use``) for the grants of tokens.
        extension: ``svg``, ``png`` or ``json``.

    Returns:
        The badge.

    Raises:
        Http404: For another extension.
    """
    if extension not in ("svg", "png", "json"):
        raise Http404("No such format")
    pipeline.refresh(
        repositories,
        user,
        reason=f"Suggestion badge {label}",
        reason_url=reason_url,
        timeout=settings.AUTO_FETCH_BADGE_TIMEOUT,
        use=use,
    )
    summary: SuggestionSummary = summary_of()
    color = NO_FEEDBACK if summary.status == GREY else COLORS[summary.status]
    data = {
        "applied": summary.applied,
        "open": summary.open,
        "unknown": summary.unknown,
        "total": summary.total,
        "status": None if summary.status == GREY else summary.status,
    }
    return BadgeSpec(label, summary.message, color, data).response(extension, BADGE_KEPT)


def public_suggestion_badge(request, scope, login, extension="svg"):
    """The badge of suggestions on the pull requests of a person in public repositories.

    Args:
        request: The request.
        scope: The text of a public scope.
        login: The author of the pull requests.
        extension: ``svg``, ``png`` or ``json``.

    Returns:
        The badge.

    Raises:
        Http404: For projects, which have their secret token.
    """
    if PROJECTS.match(scope):
        raise Http404("Projects have badges with their secret token")
    repositories = public_repositories(scope)
    return suggestion_badge_of(
        repositories,
        None,
        login,
        lambda: stats.summarize_suggestions(repositories, author=login),
        request.path,
        use=Use(TokenGrant.BADGES, scope, login),
        extension=extension,
    )


def suggestion_badge(request, token, login, extension="svg"):
    """The badge of suggestions of a person in a project: the secret token is the access.

    Args:
        request: The request.
        token: The secret badge token of the project.
        login: The author of the pull requests.
        extension: ``svg``, ``png`` or ``json``.

    Returns:
        The badge.
    """
    project = get_object_or_404(Project, badge_token=token)
    repositories = project.repositories.all()
    return suggestion_badge_of(
        repositories,
        project.user,
        login,
        lambda: stats.summarize_suggestions(repositories, author=login),
        request.path,
        extension=extension,
    )


def public_pull_suggestion_badge(request, scope, repository, number, extension="svg"):
    """The badge of suggestions of a pull request of a public repository.

    Args:
        request: The request.
        scope: The text of a public scope.
        repository: The repository as ``owner~name``.
        number: The number of the pull request.
        extension: ``svg``, ``png`` or ``json``.

    Returns:
        The badge.

    Raises:
        Http404: For projects, which have their secret token.
    """
    if PROJECTS.match(scope):
        raise Http404("Projects have badges with their secret token")
    repositories = public_repositories(scope)
    name = repository_of(repository)
    return suggestion_badge_of(
        repositories,
        None,
        f"PR #{number}",
        lambda: stats.summarize_suggestions(repositories, pull=(name, number)),
        request.path,
        use=Use(TokenGrant.BADGES, scope, ""),
        extension=extension,
    )


def pull_suggestion_badge(request, token, repository, number, extension="svg"):
    """The badge of suggestions of a pull request of a project: the token is the access.

    Args:
        request: The request.
        token: The secret badge token of the project.
        repository: The repository as ``owner~name``.
        number: The number of the pull request.
        extension: ``svg``, ``png`` or ``json``.

    Returns:
        The badge.
    """
    project = get_object_or_404(Project, badge_token=token)
    repositories = project.repositories.all()
    name = repository_of(repository)
    return suggestion_badge_of(
        repositories,
        project.user,
        f"PR #{number}",
        lambda: stats.summarize_suggestions(repositories, pull=(name, number)),
        request.path,
        extension=extension,
    )
