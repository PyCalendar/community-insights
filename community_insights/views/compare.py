from .. import pipeline, stats
from ..models import (
    Item,
)
from .scope import scope_of, scope_view, stats_page


@scope_view
def compare(request, scope):
    """One row per repository, to compare them, e.g. in an organisation."""
    scope = scope_of(request, scope)
    classifier = scope.classifier()
    rows = []
    for source in pipeline.sources(scope.repositories):
        repository = [source.repository]
        entries = stats.response_entries(repository, classifier, scope.since, scope.until)
        counted = stats.counts(repository, scope.since, scope.until)
        people = stats.contributors(repository, since=scope.since, until=scope.until)
        row = {"source": source, "counts": counted, "people": len(people)}
        for kind in (Item.PR, Item.ISSUE):
            row[f"median_{kind}"], row[f"n_{kind}"] = stats.class_percentile(
                entries[kind], None, 50
            )
            row[f"p90_{kind}"], _ = stats.class_percentile(entries[kind], None, 90)
        rows.append(row)
    sort = request.GET.get("sort", "")
    keys = {
        "name": lambda r: r["source"].repository.full_name.lower(),
        "prs": lambda r: -r["counts"]["prs"]["total"],
        "issues": lambda r: -r["counts"]["issues"]["total"],
        "people": lambda r: -r["people"],
        "response": lambda r: r["median_pr"] if r["median_pr"] is not None else float("inf"),
    }
    rows.sort(key=keys.get(sort, keys["prs"]))
    return stats_page(
        request, scope, "community/compare.html", {"rows": rows, "sort": sort or "prs"}
    )
