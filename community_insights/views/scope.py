import functools
import re
from datetime import date, datetime, time, timedelta
from urllib.parse import parse_qsl, urlencode, urlsplit

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import Resolver404, resolve, reverse
from django.utils import timezone
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from .. import data_stamp, pipeline, stats
from ..classify import Classifier, class_list, classes_by_ids, differs_from_default
from ..errors import (
    DatesInWrongOrder,
    InvalidDate,
    InvalidDateRange,
    InvalidDays,
    UnknownClasses,
)
from ..feedback import show_error
from ..models import (
    Person,
    Project,
    Repository,
)
from ..public_scope import public_scope
from .dashboard import source_choices


def date_range(parameters) -> tuple:
    """The time range of the parameters.

    Since and until (both optional, until inclusive) as times in the time zone of the browser;
    until is the start of the day after.

    Args:
        parameters: The parameters of the address, with ``since`` and ``until`` such as
            ``2026-01-31``, or ``last``: the last days, such as ``30`` for the last 30 days
            with today. All are optional; ``since`` wins over ``last``.

    Returns:
        The start and the end, each None if not given.

    Raises:
        InvalidDate: If a date cannot be read.
        InvalidDays: If the last days are no whole number above 0.
        DatesInWrongOrder: If the first date is not before the second.
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
            raise InvalidDate(
                gettext("%(text)s is no date like 2026-01-31.") % {"text": repr(text)}
            ) from None
        if name == "until":
            day += timedelta(days=1)
        found.append(
            timezone.make_aware(datetime.combine(day, time()), timezone.get_current_timezone())
        )
    since, until = found
    days = last_days(parameters)
    if since is None and days is not None:
        today = timezone.localdate()
        since = timezone.make_aware(
            datetime.combine(today - timedelta(days=days - 1), time()),
            timezone.get_current_timezone(),
        )
    if since and until and since >= until:
        raise DatesInWrongOrder(gettext("The first date is after the second."))
    return since, until


def last_days(parameters) -> int | None:
    """The number of the last days of the time range, from the parameter ``last``.

    Args:
        parameters: The parameters of the address.

    Returns:
        The days, None if not given.

    Raises:
        InvalidDays: If they are no whole number above 0.

    Examples:
        >>> last_days({"last": " 30 "}), last_days({})
        (30, None)
    """
    text = (parameters.get("last") or "").strip()
    if not text:
        return None
    if not text.isdigit() or int(text) < 1:
        raise InvalidDays(gettext("%(text)s is no number of days above 0.") % {"text": repr(text)})
    return int(text)


def drafts_of(parameters) -> bool:
    """Whether open draft pull requests count as open ones: the parameter ``drafts``.

    By default they do not: a draft is not ready for review, and its author is not expected
    to answer feedback yet.

    Args:
        parameters: The parameters of the address.

    Returns:
        True for ``drafts=1`` (also ``on``, ``yes``, ``true``).

    Examples:
        >>> drafts_of({"drafts": "1"}), drafts_of({"drafts": "on"}), drafts_of({})
        (True, True, False)
    """
    return flag_of(parameters, "drafts")


def commits_of(parameters) -> bool:
    """Whether a commit of the author is a reply to feedback: the parameter ``commits``.

    By default only text is a reply: a comment or a review comment.

    Args:
        parameters: The parameters of the address.

    Returns:
        True for ``commits=1`` (also ``on``, ``yes``, ``true``).

    Examples:
        >>> commits_of({"commits": "1"}), commits_of({})
        (True, False)
    """
    return flag_of(parameters, "commits")


def flag_of(parameters, name: str) -> bool:
    """Whether a checkbox of the address is on.

    Args:
        parameters: The parameters of the address.
        name: The parameter, such as ``drafts``.

    Returns:
        True for ``1``, ``on``, ``yes`` or ``true``.
    """
    return (parameters.get(name) or "").strip().lower() in ("1", "on", "yes", "true")


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
        """Read the scope of an address and its time range.

        Args:
            user: The user, or an anonymous one.
            text: The scope of the address, such as ``3``, ``all`` or ``plone~volto``.
            parameters: The parameters of the address: ``since`` and ``until``.

        Raises:
            PermissionDenied: If a visitor opens projects.
            Http404: If the projects are not the user's, or the public repositories are
                not known.
            InvalidDateRange: If the time range cannot be read.
        """
        self.since, self.until = date_range(parameters or {})
        given = parameters or {}
        self.last = None if (given.get("since") or "").strip() else last_days(given)
        # the classes of a shared address; None for the viewer's own
        named = (given.get("classes") or "").strip()
        self.chosen = classes_by_ids(named) if named else None
        # open drafts count as open pull requests (``drafts=1``); links carry it
        self.drafts = drafts_of(given)
        # commits of the author are replies to feedback (``commits=1``); links carry it
        self.commits = commits_of(given)
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
        if self.last:
            found["last"] = str(self.last)  # stays the last days when the link is opened later
        elif self.since:
            found["since"] = self.since.date().isoformat()
        if self.until:
            found["until"] = (self.until - timedelta(days=1)).date().isoformat()
        return found

    @functools.cached_property
    def carried(self) -> dict[str, str]:
        """The classes and the options that links carry, so a shared address shows the same.

        The classes of the address, or the own ones when they differ from the default ones;
        ``drafts=1`` when open drafts count as open pull requests, ``commits=1`` when commits
        are replies. Read once per page: a page has hundreds of links.
        """
        found = {}
        if self.chosen is not None:
            found["classes"] = " ".join(c.ident for c in self.chosen)
        elif differs_from_default(self.user):
            found["classes"] = " ".join(c.ident for c in class_list(self.user))
        if self.drafts:
            found["drafts"] = "1"
        if self.commits:
            found["commits"] = "1"
        return found

    @property
    def carried_query(self) -> str:
        """The classes for a link without a time range: "?classes=..." or ""."""
        return f"?{urlencode(self.carried)}" if self.carried else ""

    @property
    def carried_more(self) -> str:
        """The classes after other parameters: "&classes=..." or ""."""
        return f"&{urlencode(self.carried)}" if self.carried else ""

    @property
    def own_classes_query(self) -> str:
        """The time range without the classes of the address: for the own classes."""
        return f"?{urlencode(self.range)}" if self.range else ""

    @property
    def borrowed(self) -> bool:
        """Whether the page uses the classes of somebody else, from the address."""
        user_id = self.user.pk if self.user.is_authenticated else None
        return self.chosen is not None and any(c.user_id != user_id for c in self.chosen)

    @property
    def query(self) -> str:
        """The time range and the classes for links: "?since=...&classes=..." or ""."""
        found = self.range | self.carried
        return f"?{urlencode(found)}" if found else ""

    @property
    def query_more(self) -> str:
        """The time range and the classes after other parameters: "&since=..." or ""."""
        found = self.range | self.carried
        return f"&{urlencode(found)}" if found else ""

    @functools.cached_property
    def public_text(self) -> str | None:
        """The scope as visitors can open it: the public repositories, ``owner~name+...``.

        Returns:
            The text of the scope; the scope itself if it is public, None if none of its
            repositories is public.
        """
        if self.public:
            return self.text
        return scope_text(self.repositories.filter(is_private=False).order_by("full_name")) or None

    def shared(self, path: str) -> str:
        """The address of a page of this scope to share: it opens without a sign in.

        The projects are replaced by their public repositories (``public_text``), and the
        address gets the time range and the classes of the page if it does not name them, so
        that others see the same numbers. ``from`` and ``theme`` are left out.

        Args:
            path: The address on this site, such as ``/s/3/contributors/?sort=-prs_total``.

        Returns:
            The address to share; a path that is no page of a scope stays as it is, without
            ``from`` and ``theme``.
        """
        parts = urlsplit(path)
        parameters = [
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if key not in ("from", "theme")
        ]
        given = {key for key, _ in parameters}
        if not given & {"since", "until", "last"}:
            parameters += list(self.range.items())
        if "classes" not in given:
            parameters += list(self.carried.items())
        try:
            match = resolve(parts.path)
        except Resolver404:
            page = parts.path
        else:
            kwargs = dict(match.kwargs)
            if kwargs.get("scope") == self.text and self.public_text:
                kwargs["scope"] = self.public_text
            page = reverse(match.view_name, kwargs=kwargs)
        return page + (f"?{urlencode(parameters)}" if parameters else "")

    def classes(self) -> list:
        """The classes of people of the page: those of the address, or the own ones.

        Returns:
            The classes in their order, also the hidden ones.
        """
        return self.chosen if self.chosen is not None else class_list(self.user)

    def visible_classes(self) -> list:
        """The classes the statistics show: without the hidden ones.

        Returns:
            The classes in their order.
        """
        return [c for c in self.classes() if not c.hidden]

    def touch(self):
        """Remember that the repositories were used now, at most once an hour."""
        Repository.touch_all(self.repositories)

    def contributors(self, classified: bool = True) -> list:
        """The contributors of the scope, kept until the data changes (data_stamp.kept).

        Args:
            classified: Whether to give each one a class of people.

        Returns:
            The contributors (stats.Contributor).
        """
        return data_stamp.kept(
            "contributors",
            [
                sorted(self.repositories.values_list("pk", flat=True)),
                classified,
                self.user.pk if self.user.is_authenticated else "",
                [c.pk for c in self.chosen] if self.chosen is not None else None,
                self.since,
                self.until,
                self.drafts,
            ],
            lambda: stats.contributors(
                self.repositories,
                self.classifier() if classified else None,
                since=self.since,
                until=self.until,
                drafts=self.drafts,
            ),
        )

    def classifier(self) -> Classifier:
        """The classes of people of the user (the defaults for visitors), with locations.

        Returns:
            The classifier.
        """
        locations = dict(Person.objects.exclude(location="").values_list("login", "location"))
        return Classifier(self.user, locations, self.chosen)


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
    """The public scope of repositories, for an address: ``owner~name+...``.

    Args:
        repositories: The repositories.

    Returns:
        The text of the scope.
    """
    return "+".join(r.full_name.replace("/", "~") for r in repositories)


EXPORT_TABLES = [
    ("responses", _("response times")),
    ("items", _("pull requests and issues")),
    ("events", _("comments and reviews")),
    ("commits", _("commits")),
    ("contributors", _("contributors")),
]


# the quick choices of the time range: the last days
LAST_DAYS = (7, 30, 90)


def presets(path: str, scope: Scope, keep: list[tuple[str, str]]) -> list[tuple[int, str, bool]]:
    """The quick choices of the time range of a page: the last 7, 30 and 90 days.

    Args:
        path: The address of the page, without parameters.
        scope: The scope shown.
        keep: The other parameters of the page, which stay.

    Returns:
        For each choice: the days, the address, and whether the page shows it now.
    """
    return [
        (
            days,
            f"{path}?{urlencode([('last', days), *keep, *scope.carried.items()])}",
            scope.range == {"last": str(days)},
        )
        for days in LAST_DAYS
    ]


def stats_page(request, scope: Scope, template: str, context: dict):
    """A page that shows statistics and its data.

    A page that shows statistics: with how complete the data is, where it comes from, the
    running fetches and the choice of the sources.

    Args:
        request: The request.
        scope: The scope shown.
        template: The template of the page.
        context: What the template needs besides.

    Returns:
        The page.
    """
    # the date form keeps the other parameters of the page
    keep = [
        (name, value)
        for name, value in context.get("parameters", {}).items()
        if value and name not in ("since", "until", "last")
    ]
    return render(
        request,
        template,
        {
            **context,
            "scope": scope,
            "data": pipeline.completeness(scope.repositories),
            "toggles": scope_toggles(request, scope),
            "export_tables": EXPORT_TABLES,
            "keep_parameters": keep,
            "presets": presets(request.path, scope, keep),
            "choices": source_choices(request.user),
            "page_name": request.resolver_match.url_name,
            "in_scope": {p.pk for p in scope.projects},
        },
    )


def scope_toggles(request, scope: Scope) -> list[tuple]:
    """The sources of a page, each switched on or off.

    For each project: whether it is shown, and the address of this page with it switched on or
    off (None for the last one shown).

    Args:
        request: The request of the page.
        scope: The scope shown.

    Returns:
        For each project of the user: the project, whether it is shown, and the address.
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


def public_address(request, text: str) -> str | None:
    """The address of the same page for everybody, if projects have one.

    Projects whose repositories are all public have the same pages at their public scope
    (``public_scope.public_scope``); a page of them is read there, without the numbers of the
    projects. Only pages that are read (GET, HEAD), not forms that are sent.

    Args:
        request: The request.
        text: The scope of the address, such as ``1`` or ``1-2``.

    Returns:
        The address with the public scope and the same parameters; None if there is none.
    """
    if request.method not in ("GET", "HEAD") or not PROJECTS.match(text):
        return None
    match = request.resolver_match
    if match is None or match.kwargs.get("scope") != text:
        return None
    if text == "all":
        if not request.user.is_authenticated:
            return None
        projects = list(request.user.projects.all())
    else:
        ids = {int(part) for part in text.split("-")}
        projects = list(Project.objects.filter(pk__in=ids))
        if len(projects) != len(ids):
            return None
    public = public_scope(projects)
    if not public:
        return None
    path = reverse(match.view_name, kwargs={**match.kwargs, "scope": public})
    query = request.META.get("QUERY_STRING", "")
    return f"{path}?{query}" if query else path


def scope_view(view):
    """A view of a scope: public scopes for everybody, projects after a sign in.

    A page of projects that are all public leads to the same page of their public scope.

    Args:
        view: The view; its second argument is the text of the scope.

    Returns:
        The view, sending visitors who open a project to the sign in.
    """

    @functools.wraps(view)
    def checked(request, *args, **kwargs):
        text = kwargs.get("scope", args[0] if args else "")
        public = public_address(request, str(text))
        if public:
            return redirect(public)
        try:
            return view(request, *args, **kwargs)
        except PermissionDenied:
            if request.user.is_authenticated:
                raise
            return redirect_to_login(request.get_full_path())

    return checked


def scope_of(request, text: str) -> Scope:
    """The projects of the address and the time range.

    The projects of the address, the time range and the classes of its parameters; a range
    or classes that cannot be read are shown as an error and not used.

    Args:
        request: The request, with the time range in its address.
        text: The scope of the address.

    Returns:
        The scope, marked as used now.
    """
    parameters = request.GET.dict()
    for _attempt in range(3):  # each part that cannot be read is left out once
        try:
            scope = Scope(request.user, text, parameters)
            break
        except InvalidDateRange as error:
            show_error(request, error)
            parameters = {
                k: v for k, v in parameters.items() if k not in ("since", "until", "last")
            }
        except UnknownClasses as error:
            show_error(request, error)
            parameters = {k: v for k, v in parameters.items() if k != "classes"}
    else:
        scope = Scope(request.user, text)
    scope.touch()
    return scope
