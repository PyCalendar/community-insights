"""Reading repositories into the database."""

import pytest

from community_insights import stats
from community_insights.models import Event, Item, Person, Project, Repository
from community_insights.sync import read_repository, store_repository

from ..fakes import FakeClient, item, node, repo

pytestmark = pytest.mark.django_db


T0 = "2026-01-05T10:00:00Z"  # a Monday


def test_sync_stores_items_events_and_people(synced):
    assert Item.objects.filter(kind="pr").count() == 2
    assert Item.objects.get(kind="pr", number=1).merged
    assert Event.objects.filter(item__kind="pr", item__number=1).count() == 4
    assert Person.objects.get(login="bob").location == "Berlin"
    assert Person.objects.get(login="ci[bot]").is_bot
    assert synced.prs_synced_until is not None


def test_second_sync_reads_only_changes(synced, user):
    client = FakeClient(prs=[item(1, "bob", T0, reviews=[], updated="2026-01-05T12:00:00Z")])
    read_repository(client, synced)
    # nothing is newer than the stored time: the existing events stay
    assert Event.objects.filter(item__kind="pr", item__number=1).count() == 4


def test_fetch_updates_the_database(user, signed_in, monkeypatch):
    """Confirm the estimate, the job runs (inline in tests); GitHub is mocked.
    A second fetch changes nothing: same rows, no duplicates."""
    repository = store_repository(repo("o/r"))
    project = Project.objects.create(user=user, target="o/r")
    project.repositories.add(repository)
    fake = FakeClient(
        prs=[
            item(
                1,
                "bob",
                T0,
                reviews=[node("m", "2026-01-05T11:00:00Z", "OWNER", key="submittedAt")],
            )
        ],
        issues=[item(1, "bob", T0)],
    )
    monkeypatch.setattr("community_insights.github.Client", lambda token: fake)
    page = signed_in.get(f"/s/{project.pk}/fetch/")
    assert page.status_code == 200 and b"API points" in page.content
    response = signed_in.post(f"/s/{project.pk}/fetch/", {"next": f"/s/{project.pk}/"})
    assert response.status_code == 302 and response["Location"] == f"/s/{project.pk}/"
    assert Item.objects.count() == 2 and Event.objects.filter(kind="review").count() == 1
    job = repository.fetch_jobs.get()
    assert job.status == "done" and job.items_done == 2 and job.points_used > 0
    before = Event.objects.count()
    signed_in.post(f"/s/{project.pk}/fetch/", {"next": f"/s/{project.pk}/"})
    assert Event.objects.count() == before and Item.objects.count() == 2
    repository.refresh_from_db()
    assert repository.prs_total == 1 and repository.issues_total == 1


def test_items_of_deleted_users(user):  # noqa: F811
    ghost = item(1, "x", "2026-01-01T00:00:00Z", reviews=[])
    ghost["author"] = None
    ghost["comments"]["nodes"] = [
        {"createdAt": "2026-01-02T00:00:00Z", "author": None, "authorAssociation": "NONE"}
    ]
    repository = store_repository(repo("o/r"))
    read_repository(FakeClient(prs=[ghost]), repository)
    stored = Item.objects.get()
    assert stored.author == "" and stored.events.count() == 0
    assert stats.contributors(Repository.objects.all()) == []
