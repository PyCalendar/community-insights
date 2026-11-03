from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django_tables2 import RequestConfig

from .. import pipeline, stats
from ..badge_spec import BadgeSpec
from ..classify import Classifier
from ..errors import InvalidInput
from ..feedback import show_error
from ..models import AccessToken, Person, Project, TokenGrant
from ..stats.contributor_replies import GREEN, RED, YELLOW
from ..tables import ItemTable, PersonItemFilter, items_with_responses
from ..tokens.use import Use
from .access import add_grant
from .scope import PROJECTS, Scope, public_repositories, scope_of, scope_view, stats_page

COLORS = {GREEN: "#2da44e", YELLOW: "#bf8700", RED: "#cf222e"}
NO_FEEDBACK = "#9f9f9f"
# the names of the keys the table can be sorted by, as the titles of its columns
SORT_NAMES = {
    "badge": gettext_lazy("Badge"),
    "person": gettext_lazy("Person"),
    "replied": gettext_lazy("PRs replied to"),
    "merged": gettext_lazy("PRs merged"),
    "open": gettext_lazy("Not replied to and open"),
    "closed": gettext_lazy("Not replied to and closed"),
}
BADGE_KEPT = 3600  # seconds browsers and the image proxy of GitHub keep a badge


def owner_of(scope: Scope):
    """Whose tokens fetch for a page of the scope: the owner of its projects.

    Args:
        scope: The scope.

    Returns:
        The user of the projects; None for public repositories, which use the shared tokens.
    """
    return None if scope.public else scope.projects[0].user


def page_use(scope: Scope) -> Use | None:
    """The public use of a page: the grants for the public pages of its scope.

    Args:
        scope: The scope.

    Returns:
        The use; None for projects, which fetch with the tokens of their owner.
    """
    return Use(TokenGrant.PAGES, scope.text) if scope.public else None


def public_badge_scope(scope: Scope) -> str | None:
    """The public scope of the badges of a page, if they have a public address.

    Args:
        scope: The scope of the page.

    Returns:
        The text of the public scope; None for one project, whose badge has its secret token.
    """
    if scope.public:
        return scope.text
    if len(scope.projects) == 1:
        return None
    return scope.public_text


def badge_path(scope: Scope, login: str, extension: str = "svg") -> str | None:
    """The path of the badge of a person, for everybody.

    A project has its secret badge token: its classes and tokens; public repositories have
    a public address; several projects together only their public repositories.

    Args:
        scope: The scope of the page.
        login: The handle of the person.
        extension: ``svg``, ``png`` or ``json``.

    Returns:
        The path; None if the scope has neither one project nor public repositories.
    """
    public = public_badge_scope(scope)
    if public:
        return reverse("public_reply_badge_as", args=[public, login, extension])
    if not scope.public and len(scope.projects) == 1:
        return reverse("reply_badge_as", args=[scope.projects[0].badge_token, login, extension])
    return None


def sorting(request, scope: Scope, keys: list[str]) -> list[tuple]:
    """The keys of the order of the table, each with the addresses that move it.

    Args:
        request: The request.
        scope: The scope, whose time range and classes the addresses keep.
        keys: The keys in their order.

    Returns:
        For each key: the key, its name, and the addresses with it one place up and down
        (None at the ends).
    """

    def address(order: list[str]) -> str:
        """The address of the page sorted in this order."""
        parameters = {**scope.range, **scope.carried, "order": " ".join(order)}
        return f"{request.path}?{urlencode(parameters)}"

    found = []
    for index, key in enumerate(keys):
        up = down = None
        if index:
            moved = keys[: index - 1] + [key, keys[index - 1]] + keys[index + 1 :]
            up = address(moved)
        if index < len(keys) - 1:
            moved = keys[:index] + [keys[index + 1], key] + keys[index + 2 :]
            down = address(moved)
        found.append((key, SORT_NAMES[key], up, down))
    return found


@scope_view
def replies(request, scope):
    """Whether the authors of pull requests answered the comments and reviews they got.

    What changed on GitHub is fetched first, waiting a few seconds at most.

    Args:
        request: The request, with the time range.
        scope: The text of the scope.

    Returns:
        The page.
    """
    scope = scope_of(request, scope)
    fetched = pipeline.refresh(
        scope.repositories,
        owner_of(scope),
        reason=_("Replies of %(title)s") % {"title": scope.title},
        reason_url=request.path,
        use=page_use(scope),
    )
    pulls = stats.pull_replies(scope.repositories, scope.classifier(), scope.since, scope.until)
    keys = stats.sort_order(
        word for value in request.GET.getlist("order") for word in value.replace(",", " ").split()
    )
    people = stats.replies_of(pulls, keys)
    return stats_page(
        request,
        scope,
        "community/replies.html",
        {
            "people": people,
            "authors": len({pull.author.lower() for pull in pulls}),
            "sorting": sorting(request, scope, keys),
            "fetched": fetched,
            "commits_unread": stats.commits_unread(scope.repositories),
            "counts": {
                status: sum(1 for p in people if p.status == status)
                for status in (GREEN, YELLOW, RED)
            },
        },
    )


@scope_view
def person_replies(request, scope, login):
    """The pull requests of a person and whether the person answered the feedback on them.

    Those without reply first, the open ones before the closed ones. What changed on GitHub
    is fetched first, waiting a few seconds at most.

    Args:
        request: The request, with the time range.
        scope: The text of the scope.
        login: The handle of the person.

    Returns:
        The page.
    """
    scope = scope_of(request, scope)
    fetched = pipeline.refresh(
        scope.repositories,
        owner_of(scope),
        reason=_("Replies of %(login)s") % {"login": login},
        reason_url=request.path,
        use=page_use(scope),
    )
    pulls = stats.pull_replies(
        scope.repositories, scope.classifier(), scope.since, scope.until, login=login
    )
    found = stats.replies(
        scope.repositories, scope.classifier(), scope.since, scope.until, login=login
    )
    return stats_page(
        request,
        scope,
        "community/person_replies.html",
        {
            "login": login,
            "name": Person.objects.filter(login__iexact=login)
            .values_list("name", flat=True)
            .first(),
            "person": found[0] if found else None,
            "pulls": sorted(pulls, key=stats.pull_order),
            "preview": badge_path(scope, login),
            "fetched": fetched,
        },
    )


@scope_view
def reply_badge_share(request, scope, login):
    """The badge of a person with the code to copy, linked to the page of replies.

    Args:
        request: The request.
        scope: The text of the scope.
        login: The handle of the person.

    Returns:
        The page.
    """
    scope = scope_of(request, scope)
    page = request.build_absolute_uri(
        scope.shared(reverse("person_replies", args=[scope.text, login]))
    )
    image_format = "png" if request.GET.get("format") == "png" else "svg"
    path = badge_path(scope, login, image_format)
    json_path = badge_path(scope, login, "json")
    public = public_badge_scope(scope)
    signed_in = request.user.is_authenticated
    if request.method == "POST" and public and signed_in:
        stored = get_object_or_404(AccessToken, pk=request.POST.get("id"), user=request.user)
        try:
            add_grant(
                stored,
                {
                    "kind": TokenGrant.BADGES,
                    "scope": public,
                    "login": login if request.POST.get("which") == "badge" else "",
                    "percent": request.POST.get("percent"),
                },
            )
            messages.success(request, _("The public use was added."))
        except InvalidInput as error:  # shown with what to do
            show_error(request, error)
        return redirect(request.get_full_path())
    use = Use(TokenGrant.BADGES, public or "", login)
    return stats_page(
        request,
        scope,
        "community/reply_badge.html",
        {
            "public_scope": public,
            "scope_name": (public or "").replace("~", "/").replace("+", ", "),
            "own_tokens": list(request.user.access_tokens.all()) if signed_in else [],
            "own_grants": [
                g
                for g in TokenGrant.objects.filter(
                    token__user=request.user, kind=TokenGrant.BADGES
                ).select_related("token")
                if g.covers(use)
            ]
            if public and signed_in
            else [],
            "login": login,
            "name": Person.objects.filter(login__iexact=login)
            .values_list("name", flat=True)
            .first(),
            "preview": path,  # this site loads its images by their path
            "image_format": image_format,
            "json_url": request.build_absolute_uri(json_path) if json_path else None,
            "image": request.build_absolute_uri(path) if path else None,
            "page": page,
            "alt": _("Replies of %(login)s") % {"login": login},
        },
    )


@scope_view
def person_items(request, scope, login):
    """The pull requests, issues or both of one person, with their first response.

    Args:
        request: The request: ``kind`` (``pr``, ``issue`` or nothing for both), ``state``.
        scope: The text of the scope.
        login: The handle of the person.

    Returns:
        The page.
    """
    scope = scope_of(request, scope)
    found = PersonItemFilter(
        request.GET,
        queryset=items_with_responses(
            scope.repositories, scope.since, scope.until, scope.classifier()
        ).filter(author__iexact=login),
    )
    table = ItemTable(found.qs)
    # django-tables2 takes the options of the paginator; its type hints say only bool
    RequestConfig(request, paginate={"per_page": 50}).configure(table)  # pyright: ignore[reportArgumentType]
    return stats_page(
        request,
        scope,
        "community/person_items.html",
        {
            "table": table,
            "filter": found,
            "login": login,
            "parameters": dict(request.GET.items()),
        },
    )


def reply_badge_of(
    repositories, user, login: str, reason_url: str, use=None, extension="svg", page=None
) -> HttpResponse:
    """The badge of whether a person answered feedback, after fetching what changed.

    Args:
        repositories: The repositories.
        user: Whose classes and tokens count; None for the default classes and shared tokens.
        login: The handle of the person.
        reason_url: The address of the badge, for the page Downloads.
        use: The public use of the badge (``tokens.Use``): the grants of tokens for it read.
        extension: ``svg``, ``png``, or ``json`` for its spec with the row of the table.
        page: The address of the replies of the person, for the JSON; None if not public.

    Returns:
        The badge: green, yellow or red; grey without feedback.
    """
    pipeline.refresh(
        repositories,
        user,
        reason=f"Badge of {login}",
        reason_url=reason_url,
        timeout=settings.AUTO_FETCH_BADGE_TIMEOUT,
        use=use,
    )
    found = stats.replies(repositories, Classifier(user), login=login)
    person = found[0] if found else None
    if person is None:
        value, color = "no feedback yet", NO_FEEDBACK
    else:
        # in English, as the badges in READMEs: unanswered of those with feedback
        value = f"{person.unanswered_count}/{person.with_feedback} PRs unanswered"
        color = COLORS[person.status]
    data = reply_data(login, person, page)
    return BadgeSpec(login, value, color, data).response(extension, BADGE_KEPT)


def reply_data(login: str, person, page: str | None) -> dict:
    """The row of the table of replies of a person, for the JSON of the badge.

    Args:
        login: The handle of the person.
        person: The replies of the person (``stats.ContributorReplies``); None without feedback.
        page: The address of the replies of the person; None if not public.

    Returns:
        The data.
    """
    found = {"login": login, "page": page, "status": None}
    if person is not None:
        found |= {
            "status": person.status,
            "pull_requests": person.total,
            "merged": person.merged,
            "counted": person.prs,
            "with_feedback": person.with_feedback,
            "replied": person.answered,
            "not_replied": person.unanswered_count,
            "not_replied_open": person.unanswered_open,
            "not_replied_closed": person.unanswered_closed,
            "closed_by_others": person.closed_by_others,
        }
    return found


def reply_badge(request, token, login, extension="svg"):
    """The badge of replies of a person in a project: the secret token is the access.

    Args:
        request: The request.
        token: The secret badge token of the project.
        login: The handle of the person.
        extension: ``svg``, ``png`` or ``json``.

    Returns:
        The badge.
    """
    project = get_object_or_404(Project, badge_token=token)
    return reply_badge_of(
        project.repositories.all(),
        project.user,
        login,
        request.path,
        extension=extension,
    )


def public_reply_badge(request, scope, login, extension="svg"):
    """The badge of replies of a person in public repositories, with the default classes.

    Args:
        request: The request.
        scope: The text of a public scope.
        login: The handle of the person.
        extension: ``svg``, ``png`` or ``json``.

    Returns:
        The badge.

    Raises:
        Http404: If the scope is no public one or none of it is known.
    """
    if PROJECTS.match(scope):
        raise Http404("Projects have badges with their secret token")
    return reply_badge_of(
        public_repositories(scope),
        None,
        login,
        request.path,
        use=Use(TokenGrant.BADGES, scope, login),
        extension=extension,
        page=request.build_absolute_uri(reverse("person_replies", args=[scope, login])),
    )
