from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext, ngettext
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django_htmx.http import HttpResponseClientRefresh

from .. import errors, pipeline, user_limit
from ..errors import (
    FetchLimitRequired,
    InvalidExtraPoints,
    LimitNotANumber,
    UserItemsLimitReached,
    VisitorLimitReached,
)
from ..feedback import error_json, show_error
from ..github.anonymous import SERVER_QUOTA
from ..models import FetchJob, Profile
from ..models.profile import HOUR
from ..stats import format_duration
from ..tokens import points_left
from ..visitor_limit import VisitorLimit
from .dashboard import add_project_for
from .scope import scope_of, scope_view

RETURN_PAGES = ("overview", "contributors")


def whole_above_zero(text: str) -> int | None:
    """A whole number above 0 from a form.

    Args:
        text: The text of the field.

    Returns:
        The number, None if the text is no whole number above 0.

    Examples:
        >>> whole_above_zero("12"), whole_above_zero("0"), whole_above_zero("x")
        (12, None, None)
    """
    try:
        number = int(text)
    except ValueError:
        return None
    return number if number >= 1 else None


def safe_next(request, default: str) -> str:
    """Where to go back to: the next parameter if it is on this site, else the default.

    Args:
        request: The request, with ``next`` in the form or the address.
        default: Where to go otherwise.

    Returns:
        The address to go back to.
    """
    target = request.POST.get("next") or request.GET.get("next") or default
    if url_has_allowed_host_and_scheme(target, {request.get_host()}, request.is_secure()):
        return target
    return default


@scope_view
def fetch(request, scope):
    """GET: estimate the API points and the time, and ask. POST: queue.

    Args:
        request: The request: ``limit``, ``priority`` and ``next``; or ``action=allow`` with
            ``extra`` points of your tokens for this hour.
        scope: The text of the scope, such as ``3`` or ``plone~volto``.

    Returns:
        The page with the estimate, or a redirect back after queueing.
    """
    scope = scope_of(request, scope)
    back = safe_next(request, f"/s/{scope.text}/")
    visitor = not request.user.is_authenticated  # only the tokens donated to the site
    profile = None if visitor else Profile.of(request.user)
    try:
        estimates, tokens, spent = pipeline.estimate_for(request.user, scope.repositories)
    except Exception as error:  # shown with what to do
        show_error(request, error)
        return redirect(back)
    points = sum(e.points for e in estimates)
    # above the number of the profile, a fetch needs a limit, and that number is proposed
    ask_above = profile.fetch_limit if profile else pipeline.ASK_ABOVE
    if request.method == "POST" and request.POST.get("action") == "allow" and profile:
        extra = whole_above_zero(request.POST.get("extra", ""))
        if extra is None:
            show_error(
                request, InvalidExtraPoints(gettext("Allow a whole number of points above 0."))
            )
        else:
            now = timezone.now()
            profile.allow_extra(extra, now)
            profile.save()
            until = timezone.localtime(now + HOUR)
            messages.success(
                request,
                _("%(extra)s more points of your tokens are fine until %(until)s.")
                % {"extra": extra, "until": f"{until:%H:%M}"},
            )
        return redirect(f"{request.path}?next={back}")
    if request.method == "POST":
        limit_text = request.POST.get("limit", "").strip()
        limit = whole_above_zero(limit_text) if limit_text else None
        if limit_text and limit is None:
            show_error(
                request,
                LimitNotANumber(
                    gettext("%(limit_text)s is no whole number above 0.")
                    % {"limit_text": repr(limit_text)}
                ),
            )
            return redirect(f"{request.path}?next={back}")
        if points > ask_above and limit is None:
            show_error(
                request,
                FetchLimitRequired(
                    gettext("This fetch needs about %(points)s points.") % {"points": points}
                ),
            )
            return redirect(f"{request.path}?next={back}")
        try:
            priority = int(request.POST.get("priority", FetchJob.NORMAL))
        except ValueError:
            priority = FetchJob.NORMAL
        if not visitor:
            try:
                user_limit.check(request.user, sum(e.missing for e in estimates))
            except UserItemsLimitReached as error:
                show_error(request, error)
                return redirect(back)
        if visitor:  # the donated tokens go to the people with accounts first
            priority = FetchJob.LOW
            try:
                VisitorLimit("fetch", settings.VISITOR_FETCHES_PER_HOUR).count(request)
            except VisitorLimitReached as error:
                show_error(request, error)
                return redirect(back)
        jobs = pipeline.enqueue(
            None if visitor else request.user,
            estimates,
            priority=max(FetchJob.LOW, min(FetchJob.HIGH, priority)),
            point_limit=limit,
            reason=request.POST.get("reason", "")[:300] or f"Statistics of {scope.title}",
            reason_url=back,
        )
        messages.info(
            request,
            ngettext("%(count)s repository queued.", "%(count)s repositories queued.", len(jobs))
            % {"count": len(jobs)}
            if jobs
            else _("Everything is already queued."),
        )
        return redirect(back)
    seconds = points * pipeline.seconds_per_point()
    anonymous = not tokens
    if anonymous:  # the quota of this server without a token
        quota = SERVER_QUOTA.remaining if SERVER_QUOTA.remaining is not None else 60
        left = {"own": 0, "shared": 0, "total": quota, "unlimited": False}
    else:
        left = points_left(tokens, timezone.now())
    short = not left["unlimited"] and points > left["total"]
    return render(
        request,
        "community/fetch.html",
        {
            "scope": scope,
            "estimates": estimates,
            "points": points,
            "left": left,
            "short": short,
            "anonymous": anonymous,
            "visitor": visitor,
            "missing_points": max(0, points - left["total"]),
            "extra_left": profile.extra_left(timezone.now()) if profile else 0,
            "duration": format_duration(seconds),
            "ask_limit": points > ask_above,
            "items_limit": None if visitor else user_limit.limit_of(request.user),
            "items_held": 0 if visitor else user_limit.items_of(request.user),
            "default_limit": ask_above,
            "ask_above": ask_above,
            "tokens": tokens,
            "spent_on_estimate": spent,
            "next": back,
            "priorities": FetchJob.PRIORITIES,
        },
    )


@login_required
def downloads(request):
    """What is fetched now, what waits in the queue, and what ran.

    Args:
        request: The request; a POST cancels a job or moves it up or down.

    Returns:
        The page Downloads, or a redirect to it after a change.
    """
    jobs = FetchJob.objects.filter(user=request.user).select_related("repository")
    if request.method == "POST":
        job = get_object_or_404(jobs, pk=request.POST.get("id"))
        action = request.POST.get("action")
        if action == "cancel":
            pipeline.cancel(job)
            messages.info(
                request,
                _("%(repository)s is cancelled; what was read is kept.")
                % {"repository": job.repository},
            )
        elif action in ("up", "down") and job.status == FetchJob.QUEUED:
            reorder(job, up=action == "up")
        return redirect("downloads")
    active = list(jobs.filter(status__in=FetchJob.ACTIVE).order_by("-priority", "created"))
    running = [j for j in active if j.status == FetchJob.RUNNING]
    return render(
        request,
        "community/downloads.html",
        {
            "running": running,
            "queued": [j for j in active if j.status == FetchJob.QUEUED],
            "finished": jobs.exclude(status__in=FetchJob.ACTIVE).order_by("-finished")[:20],
            "seconds_left": pipeline.seconds_left(active),
        },
    )


def reorder(job: FetchJob, up: bool) -> None:
    """Move a queued job before the one above it, or after the one below.

    The order is the priority, so this also decides who gets the tokens first.

    Args:
        job: A queued job.
        up: True to move it before the one above, False after the one below.
    """
    queued = list(FetchJob.objects.filter(status=FetchJob.QUEUED).order_by("-priority", "created"))
    index = next(i for i, j in enumerate(queued) if j.pk == job.pk)
    other = index - 1 if up else index + 1
    if not 0 <= other < len(queued):
        return
    neighbour = queued[other]
    job.priority = neighbour.priority + (1 if up else -1)
    job.save(update_fields=["priority"])


@scope_view
@never_cache
def progress(request, scope):
    """How complete the data of a scope is: the part of the page for htmx, else JSON.

    htmx asks for the progress bar while fetches run (``_progress.html``); when they ended,
    the answer makes the browser load the page again, with the statistics of the new data.
    An error is shown in the bar, with what to do. Without htmx, the numbers come as JSON,
    an error as JSON with what to do.

    Args:
        request: The request.
        scope: The text of the scope.

    Returns:
        The progress bar, a refresh of the page, or the numbers as JSON.

    Raises:
        Http404: If there is no such scope.
    """
    try:
        data = pipeline.completeness(scope_of(request, scope).repositories)
    except Http404:
        raise
    except Exception as error:
        if request.htmx:
            return render(
                request,
                "community/_progress.html",
                {
                    "scope": {"text": scope},
                    "data": {"percent": 0, "total": None, "jobs": []},
                    "error": errors.translate(error),
                    "page_path": request.htmx.current_url_abs_path,
                },
            )
        return error_json(error)
    if request.htmx:
        if not data["jobs"]:  # the fetches ended: the statistics of the new data
            return HttpResponseClientRefresh()
        return render(
            request,
            "community/_progress.html",
            {
                "scope": {"text": scope},
                "data": data,
                "page_path": request.htmx.current_url_abs_path,
            },
        )
    return JsonResponse(
        {
            "percent": data["percent"],
            "items": data["items"],
            "total": data["total"],
            "seconds_left": data["seconds_left"],
            "jobs": [
                {
                    "repository": job.repository.full_name,
                    "status": job.status,
                    "percent": job.percent,
                    "message": job.message,
                }
                for job in data["jobs"]
            ],
        }
    )


@login_required
@require_POST
def add_source(request, scope):
    """Add a repository or organisation as a project and show it with the sources already shown.

    Args:
        request: The request, with ``target`` (``owner/name`` or ``owner``) and ``page``.
        scope: The projects shown now, such as ``1-3``.

    Returns:
        A redirect to the page with the new project shown, too.
    """
    try:
        project = add_project_for(request.user, request.POST.get("target", ""))
    except Exception as error:  # shown with what to do
        show_error(request, error)
        return redirect("overview", scope=scope)
    ids = [] if scope == "all" else scope.split("-")
    if str(project.pk) not in ids:
        ids.append(str(project.pk))
    messages.success(
        request,
        _("%(target)s was added. Read it from GitHub to see its data.")
        % {"target": project.target},
    )
    page = request.POST.get("page")
    return redirect(
        page if page in RETURN_PAGES else "overview",
        scope="-".join(ids) if scope != "all" else "all",
    )
