"""Response times, their fits and Kaplan-Meier."""

import pytest

from community_insights import stats
from community_insights.classify import Classifier
from community_insights.models import Repository

pytestmark = pytest.mark.django_db


def test_response_times_per_class(synced, user):
    """Response times per class."""
    entries = stats.response_entries(Repository.objects.all(), Classifier(user))
    pr1 = entries["pr"][0] if "bot" in entries["pr"][0] else entries["pr"][1]
    assert pr1["bot"] == 600
    assert pr1["collaborator or higher"] == 7200
    assert "external" not in pr1  # the author's own comment is no response
    assert any("external" in e for e in entries["issue"])


def test_percentile_and_summary():
    """Percentile and summary."""
    assert stats.percentile([1, 2, 3, 4], 50) == 2.5
    assert stats.percentile([], 50) is None
    rows = stats.summary([{"bot": 60.0}, {"bot": 180.0}], ["bot"])
    assert [r.fit for r in rows] == ["measured", "normal", "exponential"]
    assert rows[0].median == "2min"


def test_scipy_fits_match_the_documented_calls(world):  # noqa: F811
    """Scipy fits match the documented calls."""
    import scipy.stats

    x = [60.0, 120.0, 600.0, 3600.0]
    rows = stats.summary([{"c": v} for v in x], ["c"])
    _, scale = scipy.stats.expon.fit(x, floc=0)
    exponential = next(r for r in rows if r.fit == "exponential")
    assert exponential.average == stats.format_duration(scale)
    assert exponential.p95 == stats.format_duration(scipy.stats.expon.ppf(0.95, scale=scale))
    one = stats.summary([{"c": 60.0}], ["c"])
    assert one[0].std_error == "-" and one[1].p95 == "-"


def test_kaplan_meier_counts_the_items_without_a_response():
    """Kaplan meier counts the items without a response."""
    entries = [{"bot": 60.0}, {"bot": 120.0}, {}, {}]
    observed = [3600.0, 3600.0, 30.0, 7200.0]
    rows = stats.summary(entries, ["bot"], observed)
    km = next(r for r in rows if r.fit == "Kaplan-Meier")
    assert km.n == 4
    # the item observed for 30 seconds only leaves the risk set early
    sf = stats.survival(entries, observed, "bot")
    assert stats.quantile(sf, 0.5) == 120.0
    assert km.median == "2min" and km.p95 == "-", "95 % never got a response"
    measured = next(r for r in rows if r.fit == "measured")
    assert measured.median == "2min" and measured.n == 2
    assert stats.survival([{}], [10.0], "bot") is None


def test_the_fits_keep_their_standard_error_as_a_number():
    """The fits keep their standard error as a number."""
    rows = stats.summary([{"bot": 60.0}, {"bot": 180.0}], ["bot"], [100.0, 200.0])
    errors = {r.fit: r.error_seconds for r in rows}
    assert errors["measured"] == pytest.approx(60.0)  # scipy.stats.sem([60, 180])
    assert errors["normal"] == pytest.approx(60.0 / 2**0.5)
    assert errors["exponential"] == pytest.approx(120.0 / 2**0.5)
    assert errors["Kaplan-Meier"] is None
    one = stats.summary([{"c": 60.0}], ["c"])
    assert [r.error_seconds for r in one][:2] == [None, None]


def test_the_best_fit_has_the_lowest_standard_error_of_all_classes():
    """The best fit has the lowest standard error of all classes."""
    rows = stats.summary(
        [{"a": 60.0, "b": 60.0}, {"a": 180.0, "b": 61.0}, {"a": 400.0, "b": 62.0}], ["a", "b"]
    )
    assert stats.best_fit(rows) == "normal"
    assert stats.best_fit(stats.summary([{"c": 60.0}], ["c"])) == "exponential"
    assert stats.best_fit([]) == "measured"


def test_the_overview_selects_the_best_fit(synced, signed_in):
    """The overview selects the best fit."""
    from community_insights.models import Project

    page = signed_in.get(f"/s/{Project.objects.get().pk}/").content.decode()
    assert 'data-fit-select="#fits-pr"' in page and 'id="fits-pr"' in page
    assert '<tr data-fit="Kaplan-Meier">' in page
    assert "selected>" in page and "(lowest std error)" in page
    assert "Kaplan-Meier counts all items" in page
    assert "js/fit-select.js" in page


def test_kaplan_meier_when_every_item_got_a_response():
    """Without waiting items, the 95 % is the slowest response."""
    entries = [{"bot": 60.0}, {"bot": 120.0}, {"bot": 3600.0}]
    fitted = stats.survival(entries, [60.0, 120.0, 3600.0], "bot")
    assert stats.quantile(fitted, 0.5) == 120.0
    assert stats.quantile(fitted, 0.95) == 3600.0
    assert stats.quantile(fitted, 1.0) == 3600.0


def test_kaplan_meier_with_responses_at_once():
    """Responses after 0 seconds count; no warning stops it."""
    fitted = stats.survival([{"bot": 0.0}, {"bot": 0.0}, {}], [0.0, 0.0, 10.0], "bot")
    assert stats.quantile(fitted, 0.5) == 0.0
    assert stats.quantile(fitted, 0.95) is None


def test_kaplan_meier_of_the_first_response_of_anybody():
    """Without a class, the fastest class of an item counts."""
    entries = [{"bot": 60.0, "maintainer": 30.0}, {"maintainer": 90.0}, {}]
    fitted = stats.survival(entries, [60.0, 90.0, 1000.0], None)
    assert stats.quantile(fitted, 0.5) == 90.0
    assert stats.survival([{}, {}], [1.0, 2.0], None) is None


def test_kaplan_meier_needs_one_observation_per_item():
    """The lists must be as long as each other."""
    with pytest.raises(ValueError):
        stats.survival([{"bot": 1.0}], [1.0, 2.0], "bot")


def test_responses_by_month_of_somebody_who_never_responded(synced, user):  # noqa: F811
    """No responses: no months."""
    from datetime import UTC

    assert stats.responses_by_month(Repository.objects.all(), "nobody", UTC) == {}


def test_the_kaplan_meier_code_of_the_documentation_gives_the_same_median():
    """docs/how-to/verify.rst computes the median of Kaplan-Meier from the downloads."""
    import lifelines
    import pandas

    entries = [{"bot": 60.0}, {"bot": 600.0}, {}, {"bot": 30.0}, {}]
    observed = [60.0, 600.0, 7200.0, 30.0, 50.0]
    table = pandas.DataFrame(
        {"seconds_bot": [e.get("bot") for e in entries], "observed_seconds": observed}
    )
    # the code of the documentation
    column = table["seconds_bot"]
    durations = column.fillna(table["observed_seconds"])
    fitted = lifelines.KaplanMeierFitter().fit(durations, event_observed=column.notna())
    ours = stats.quantile(stats.survival(entries, observed, "bot"), 0.5)
    assert fitted.median_survival_time_ == ours == 600.0
