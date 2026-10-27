from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache as django_cache
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from ..cleanup import LAST_SHRINK, MB, database_size
from ..models import (
    Event,
    Person,
    Repository,
)


@login_required
def cache(request):
    """The page Cache: what was read, and deleting it; for the administrators only.

    The page Cache: what was read, from the oldest use, the size of the database, and deleting.
    It concerns everybody's data, so only staff may see it.

    Args:
        request: The request; a POST deletes a repository or what was not used for days.

    Returns:
        The page, or a redirect to it after a change.

    Raises:
        PermissionDenied: If the user is no administrator.
    """
    user = request.user
    if not user.is_staff:
        raise PermissionDenied("Only the administrators may see the cache.")
    repositories = (
        Repository.objects.all()
        if user.is_staff
        else Repository.objects.filter(projects__user=user).distinct()
    )
    if request.method == "POST":
        if "repository" in request.POST:
            repositories.filter(pk=request.POST["repository"]).delete()
        elif "days" in request.POST:
            limit = timezone.now() - timedelta(days=int(request.POST["days"]))
            repositories.filter(last_used_at__lt=limit).delete()
            if user.is_staff:
                Person.objects.filter(last_used_at__lt=limit).delete()
        messages.success(request, _("Cache cleared. It is read again when needed."))
        return redirect("cache")
    return render(
        request,
        "community/cache.html",
        {
            "repositories": repositories.annotate(n_items=Count("items", distinct=True)).order_by(
                "last_used_at"
            ),
            "people": Person.objects.count() if user.is_staff else None,
            "size_mb": round(size / MB, 1) if (size := database_size()) is not None else None,
            "limit_mb": settings.DATABASE_MAX_MB,
            "min_age_hours": settings.DATABASE_MIN_AGE_HOURS,
            "last_shrink": django_cache.get(LAST_SHRINK) if user.is_staff else None,
            "events": Event.objects.filter(item__repository__in=repositories).count(),
        },
    )
