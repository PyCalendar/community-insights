"""What people did: counts, contributors, commits."""

from datetime import UTC

import pytest

from community_insights import export, stats
from community_insights.classify import Classifier
from community_insights.models import Repository
from community_insights.sync import read_repository, store_repository

from ..fakes import FakeClient, repo

pytestmark = pytest.mark.django_db


def test_counts_and_contributors(synced, user):
    counts = stats.counts(Repository.objects.all())
    assert counts["prs"]["merged"] == 1 and counts["prs"]["open"] == 1
    people = {p.login: p for p in stats.contributors(Repository.objects.all(), Classifier(user))}
    assert people["bob"].prs_opened == 1 and people["bob"].prs_merged == 1
    assert people["bob"].location == "Berlin"
    assert people["maint"].reviews == 1
    assert people["maint"].median_response == 7200
    assert people["ci[bot]"].klass == "bot"


def test_closed_unmerged_pull_requests(world):  # noqa: F811
    counts = stats.counts(Repository.objects.all())
    assert counts["prs"] == {"total": 3, "open": 1, "merged": 1, "closed": 1}
    assert counts["issues"] == {"total": 2, "open": 2, "closed": 0}


def test_commits_are_contributions(user):  # noqa: F811
    from community_insights.models import Commit

    from ..fakes import commit

    repository = store_repository(repo("o/c"))
    client = FakeClient(
        commits=[
            commit("a" * 40, "bob", "2026-01-05T10:00:00Z"),
            commit("b" * 40, "bob", "2026-01-06T10:00:00Z"),
            commit("c" * 40, None, "2026-01-07T10:00:00Z", name="Somebody"),
        ]
    )
    assert "3 commits read" in read_repository(client, repository)
    assert Commit.objects.count() == 3
    repository.refresh_from_db()
    assert repository.commits_total == 3 and repository.commits_synced_until is not None
    assert "0 commits read" in read_repository(client, repository), "only new commits"
    people = {p.login: p for p in stats.contributors(Repository.objects.filter(pk=repository.pk))}
    assert people["bob"].commits == 2 and people["bob"].activity == 2
    kinds = [kind for _, kind in stats.activity_of([repository], "bob")]
    assert kinds == ["commit", "commit"]
    rows = export.commits([repository])
    assert [r["author"] for r in rows] == ["bob", "bob", ""] and rows[2][
        "author_name"
    ] == "Somebody"


def test_response_times_of_a_person_by_month(world, signed_in):  # noqa: F811

    months = stats.responses_by_month(Repository.objects.all(), "maint", UTC)
    assert months == {(2026, 1): [7200.0]}
    assert stats.responses_by_month(Repository.objects.all(), "bob", UTC) == {}, (
        "own items do not count"
    )
    pk = world["project"].pk
    for login in ("maint", "bob"):
        response = signed_in.get(f"/s/{pk}/chart/responses.svg?login={login}")
        assert response.status_code == 200 and b"<svg" in response.content
