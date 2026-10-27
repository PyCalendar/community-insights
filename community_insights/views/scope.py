import functools
import re
from datetime import date, datetime, time, timedelta
from urllib.parse import urlencode

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .. import pipeline
from ..classify import Classifier
from ..errors import DatesInWrongOrder, InvalidDate, InvalidDateRange
from ..feedback import show_error
from ..models import (
    Person,
    Repository,
)
from .dashboard import source_choices


def date_range(parameters) -> tuple:
    """The time range of the parameters.

    Since and until (both optional, until inclusive) as times in the time zone of the browser;
    until is the start of the day after.
    """
    found = []
    for name in ("since", "until"):
        text = (parameters.get(name) or "").strip()
        if not text:
            found.append(None)
            continue
        try:
            day = date.fromisoformat(text)
        except ValueError:
            raise InvalidDate(f"{text!r} is no date like 2026-01-31.") from None
        if name == "until":
            day += timedelta(days=1)
        found.append(
            timezone.make_aware(datetime.combine(day, time()), timezone.get_current_timezone())
        )
    since, until = found
    if since and until and since >= until:
        raise DatesInWrongOrder("The first date is after the second.")
    return since, until


PROJECTS = re.compile(r"^(all|\d+(-\d+)*)$")
# a public scope: "owner~name" or "owner", several joined with "+"
PUBLIC_PART = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})(?:~[A-Za-z0-9._-]{1,100})?$")


class Scope:
    """What a statistics page shows: projects of the user, or public repositories.

    The address names it: ``3``, ``1-2-3`` or ``all`` are projects of the user
    (they need a sign in); ``plone~volto``, ``plone`` or ``plone~volto+django`` are
    public repositories or all known public ones of an owner, for everybody.
    """

    def __init__(self, user, text: str, parameters=None):
        self.since, self.until = date_range(parameters or {})
        self.text = text
        self.user = user
        self.public = not PROJECTS.match(text)
        if self.public:
            self.projects = []
            self.repositories = public_repositories(text)
        else:
            if not user.is_authenticated:
                raise PermissionDenied("Projects are shown to their owners only.")
            projects = user.projects.all()
            if text != "all":
                projects = projects.filter(pk__in=[int(part) for part in text.split("-")])
            self.projects = list(projects)
            if not self.projects:
                raise Http404("No such project")
            self.repositories = Repository.objects.filter(projects__in=self.projects).distinct()

    @property
    def title(self) -> str:
        """The names of the projects or repositories shown."""
        if self.public:
            return ", ".join(part.replace("~", "/") for part in self.text.split("+"))
        return ", ".join(p.label for p in self.projects)

    @property
    def range(self) -> dict[str, str]:
        """The time range as it is written in the address."""
        found = {}
        if self.since:
            found["since"] = self.since.date().isoformat()
        if self.until:
            found["until"] = (self.until - timedelta(days=1)).date().isoformat()
        return found

    @property
    def query(self) -> str:
        """The time range for links: "?since=...&until=..." or ""."""
        return f"?{urlencode(self.range)}" if self.range else ""

    @property
    def query_more(self) -> str:
        """The time range after other parameters: "&since=..." or ""."""
        return f"&{urlencode(self.range)}" if self.range else ""

    def touch(self):
        """Remember that the repositories were used now."""
        self.repositories.update(last_used_at=timezone.now())

    def classifier(self) -> Classifier:
        """The classes of people of the user (the defaults for visitors), with locations."""
        locations = dict(Person.objects.exclude(location="").values_list("login", "location"))
        return Classifier(self.user, locations)


def public_repositories(text: str):
    """The known public repositories of a public scope.

    Args:
        text: ``owner~name`` or ``owner`` parts, joined with ``+``.

    Returns:
        The repositories, as a query.

    Raises:
        Http404: If the text is no public scope or none of it is known.
    """
    parts = text.split("+")
    if not all(PUBLIC_PART.match(part) for part in parts):
        raise Http404("No such scope")
    names = [part.replace("~", "/") for part in parts if "~" in part]
    owners = [part for part in parts if "~" not in part]
    found = Repository.objects.filter(is_private=False).filter(
        Q(full_name__in=names) | Q(owner_login__in=owners)
    )
    if not found.exists():
        raise Http404("None of these public repositories is known yet")
    return found


def scope_text(repositories) -> str:
    """The public scope of repositories, for an address: ``owner~name+...``."""
    return "+".join(r.full_name.replace("/", "~") for r in repositories)


EXPORT_TABLES = [
    ("responses", _("response times")),
    ("items", _("pull requests and issues")),
    ("events", _("comments and reviews")),
    ("commits", _("commits")),
    ("contributors", _("contributors")),
]


def stats_page(request, scope: Scope, template: str, context: dict):
    """A page that shows statistics and its data.

    A page that shows statistics: with how complete the data is, where it comes from, the
    running fetches and the choice of the sources.
    """
    return render(
        request,
        template,
        {
            **context,
            "scope": scope,
            "data": pipeline.completeness(scope.repositories),
            "toggles": scope_toggles(request, scope),
            "export_tables": EXPORT_TABLES,
            # the date form keeps the other parameters of the page
            "keep_parameters": [
                (name, value)
                for name, value in context.get("parameters", {}).items()
                if value and name not in ("since", "until")
            ],
            "choices": source_choices(request.user),
            "page_name": request.resolver_match.url_name,
            "in_scope": {p.pk for p in scope.projects},
        },
    )


def scope_toggles(request, scope: Scope) -> list[tuple]:
    """The sources of a page, each switched on or off.

    For each project: whether it is shown, and the address of this page with it switched on or
    off (None for the last one shown).
    """
    if scope.public or not request.user.is_authenticated:
        return []
    shown = {p.pk for p in scope.projects}
    match = request.resolver_match
    result = []
    for project in request.user.projects.all():
        ids = shown ^ {project.pk}
        href = None
        if ids:
            kwargs = {**match.kwargs, "scope": "-".join(map(str, sorted(ids)))}
            href = reverse(match.url_name, kwargs=kwargs) + scope.query
        result.append((project, project.pk in shown, href))
    return result


def scope_view(view):
    """A view of a scope: public scopes for everybody, projects after a sign in.

    Args:
        view: The view; its second argument is the text of the scope.

    Returns:
        The view, sending visitors who open a project to the sign in.
    """

    @functools.wraps(view)
    def checked(request, *args, **kwargs):
        try:
            return view(request, *args, **kwargs)
        except PermissionDenied:
            if request.user.is_authenticated:
                raise
            return redirect_to_login(request.get_full_path())

    return checked


def scope_of(request, text: str) -> Scope:
    """The projects of the address and the time range.

    The projects of the address and the time range of its parameters; a range that cannot be
    read is shown as an error and not used.
    """
    try:
        scope = Scope(request.user, text, request.GET)
    except InvalidDateRange as error:
        show_error(request, error)
        scope = Scope(request.user, text)
    scope.touch()
    return scope
