"""Response times, their fits and Kaplan-Meier."""

import pytest

from community_insights import stats
from community_insights.classify import Classifier
from community_insights.models import Repository

pytestmark = pytest.mark.django_db


def test_response_times_per_class(synced, user):
    entries = stats.response_entries(Repository.objects.all(), Classifier(user))
    pr1 = entries["pr"][0] if "bot" in entries["pr"][0] else entries["pr"][1]
    assert pr1["bot"] == 600
    assert pr1["collaborator or higher"] == 7200
    assert "external" not in pr1  # the author's own comment is no response
    assert any("external" in e for e in entries["issue"])


def test_percentile_and_summary():
    assert stats.percentile([1, 2, 3, 4], 50) == 2.5
    assert stats.percentile([], 50) is None
    rows = stats.summary([{"bot": 60.0}, {"bot": 180.0}], ["bot"])
    assert [r.fit for r in rows] == ["measured", "normal", "exponential"]
    assert rows[0].median == "2min"


def test_scipy_fits_match_the_documented_calls(world):  # noqa: F811
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
