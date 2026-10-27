from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from .. import pipeline
from ..errors import FetchLimitRequired, InvalidExtraPoints, LimitNotANumber
from ..feedback import error_json, show_error
from ..github.anonymous import SERVER_QUOTA
from ..models import FetchJob, Profile
from ..models.profile import HOUR
from ..stats import format_duration
from ..tokens import points_left
from .dashboard import add_project_for
from .scope import scope_of, scope_view

RETURN_PAGES = ("overview", "contributors")


def safe_next(request, default: str) -> str:
    """Where to go back to: the next parameter if it is on this site, else the default."""
    target = request.POST.get("next") or request.GET.get("next") or default
    if url_has_allowed_host_and_scheme(target, {request.get_host()}, request.is_secure()):
        return target
    return default


@scope_view
def fetch(request, scope):
    """GET: estimate the API points and the time, and ask. POST: queue."""
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
    if request.method == "POST" and request.POST.get("action") == "allow" and profile:
        try:
            extra = int(request.POST.get("extra", ""))
            if extra < 1:
                raise ValueError
        except ValueError:
            show_error(request, InvalidExtraPoints("Allow a whole number of points above 0."))
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
        try:
            limit = int(limit_text) if limit_text else None
            if limit is not None and limit < 1:
                raise ValueError
        except ValueError:
            show_error(request, LimitNotANumber(f"{limit_text!r} is no whole number above 0."))
            return redirect(f"{request.path}?next={back}")
        if points > pipeline.ASK_ABOVE and limit is None:
            show_error(request, FetchLimitRequired(f"This fetch needs about {points} points."))
            return redirect(f"{request.path}?next={back}")
        try:
            priority = int(request.POST.get("priority", FetchJob.NORMAL))
        except ValueError:
            priority = FetchJob.NORMAL
        if visitor:  # the donated tokens go to the people with accounts first
            priority = FetchJob.LOW
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
            "ask_limit": points > pipeline.ASK_ABOVE,
            "default_limit": profile.fetch_limit if profile else pipeline.ASK_ABOVE,
            "ask_above": pipeline.ASK_ABOVE,
            "tokens": tokens,
            "spent_on_estimate": spent,
            "next": back,
            "priorities": FetchJob.PRIORITIES,
        },
    )


@login_required
def downloads(request):
    """What is fetched now, what waits in the queue, and what ran."""
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
    """How complete the data of a scope is, as JSON.

    How complete the data of a scope is, for the progress bar; an error as JSON with what to do
    (static/js/progress.js shows it).
    """
    try:
        data = pipeline.completeness(scope_of(request, scope).repositories)
    except Http404:
        raise
    except Exception as error:
        return error_json(error)
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
    """Add a repository or organisation as a project and show it with the sources already shown."""
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
