"""The page Reviews: how many reviews, by collaborators and by others, and until a merge."""

from datetime import timedelta

from django.utils import timezone
from django.utils.translation import gettext as _

from .. import stats
from ..stats.periods import previous
from .charts import REVIEW_KINDS
from .scope import scope_of, scope_view, stats_page
from .statistics import BAR_CHOICES, PER, bars_of


@scope_view
def reviews(request, scope):
    """The reviews of pull requests in the time range, next to the time before it.

    Args:
        request: The request, with the time range and ``by``, the length of the bars.
        scope: The text of the scope.

    Returns:
        The page.
    """
    scope = scope_of(request, scope)
    now = timezone.now()
    by = bars_of(request)
    numbers = stats.review_numbers(scope.repositories, scope.since, scope.until, now)
    series = stats.review_series(
        scope.repositories, scope.since, scope.until, now, timezone.get_current_timezone(), by
    )
    models = [
        (
            name,
            what,
            stats.count_trend(series[name], series["exposure"], series["size"]),
        )
        for name, what in (
            ("total", _("Reviews")),
            ("collaborators", _("Reviews by collaborators")),
            ("others", _("Reviews by others")),
        )
    ]
    before = previous(scope.since, scope.until, now)
    return stats_page(
        request,
        scope,
        "community/reviews.html",
        {
            "scope": scope,
            "numbers": numbers,
            "models": models,
            "per": PER.get(series["size"], ""),
            "by": by,
            "bar_choices": BAR_CHOICES,
            "chart_query": scope.query + (("&" if scope.query else "?") + f"by={by}" if by else ""),
            "parameters": {"by": by},
            "kind_names": [(kind, str(title)) for kind, title in REVIEW_KINDS.items()],
            "before": [
                timezone.localdate(before[0]),
                timezone.localdate(before[1] - timedelta(microseconds=1)),
            ]
            if before
            else None,
        },
    )
