"""How fast the statistics are with much data (made up, like `make run-prepare`)."""

import pytest
from django.utils import timezone

from community_insights import export, query, stats
from community_insights.classify import Classifier, ensure_default_classes
from community_insights.demo import DemoClient
from community_insights.models import Project, Repository
from community_insights.sync import read_repository, store_repository

from ..data import signed_in, user  # noqa: F401

pytestmark = [pytest.mark.performance, pytest.mark.django_db]

LIMIT = {  # seconds
    "read 5000 made up items": 60,
    "response times": 3,
    "contributors": 3,
    "query": 3,
    "overview page": 6,
    "contributors page": 6,
    "items page": 6,
    "chart": 4,
    "export responses": 5,
}


@pytest.fixture
def large(user):  # noqa: F811
    """A project with many made up items."""
    ensure_default_classes(user)
    repository = store_repository({"nameWithOwner": "demo/large", "stargazerCount": 1})
    project = Project.objects.create(user=user, target="demo/large")
    project.repositories.add(repository)
    return project


def test_statistics_of_5000_items(large, user, signed_in, timer):  # noqa: F811
    """Statistics of 5000 items."""
    repositories = Repository.objects.all()
    with timer("read 5000 made up items"):
        read_repository(DemoClient(seed=7, prs=3000, issues=2000), repositories.get())
    classifier = Classifier(user)
    with timer("response times"):
        stats.response_entries(repositories, classifier)
    with timer("contributors"):
        people = stats.contributors(repositories, classifier)
    with timer("query"):
        query.run(people, timezone.now(), where="prs_merged > 1", group="class")
    for name, url in [
        ("overview page", f"/s/{large.pk}/"),
        ("contributors page", f"/s/{large.pk}/contributors/"),
        ("items page", f"/s/{large.pk}/items/"),
        ("chart", f"/s/{large.pk}/chart/responses-pr.svg"),
    ]:
        with timer(name):
            assert signed_in.get(url).status_code == 200
    with timer("export responses"):
        export.table("responses", repositories, classifier, ["bot"])
    slow = {name: t for name, t in timer.times.items() if t > LIMIT[name]}
    assert not slow, f"slower than {LIMIT}: {slow}"
