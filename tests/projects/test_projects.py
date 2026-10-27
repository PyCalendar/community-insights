"""Adding, renaming and removing projects; only public repositories."""

import pytest

from community_insights.errors import InvalidTarget
from community_insights.models import Project
from community_insights.sync import add_project

from ..fakes import FakeClient, repo, run

pytestmark = pytest.mark.django_db


def test_add_project_owner_and_repo(user):
    client = FakeClient(repositories=[repo("o/a", 9), repo("o/b", 1, private=True)])
    project = run(add_project, user, client, "o")
    # for now only public repositories: the private one of the organisation is skipped
    assert project.is_owner and project.repositories.count() == 1 and not project.is_private
    single = run(add_project, user, client, "https://github.com/o/a")
    assert single.target == "o/a" and single.repositories.count() == 1
    with pytest.raises(InvalidTarget):
        run(add_project, user, client, "a/b/c")


def test_rename_a_project(world, signed_in):  # noqa: F811
    pk = world["project"].pk
    signed_in.post(f"/projects/{pk}/rename/", {"name": "Our tool"})
    assert Project.objects.get(pk=pk).label == "Our tool"
    page = signed_in.get(f"/s/{pk}/").content.decode()
    assert "Our tool" in page
    signed_in.post(f"/projects/{pk}/rename/", {"name": "  "})
    assert Project.objects.get(pk=pk).label == "o/r"
    assert signed_in.get(f"/projects/{pk}/rename/").status_code == 405


def test_private_repositories_are_refused_for_now(user, settings):  # noqa: F811
    from community_insights.errors import PrivateRepositoryRefused, RepositoryNotFound

    client = FakeClient(repositories=[repo("o/secret", private=True)])
    with pytest.raises(PrivateRepositoryRefused):
        run(add_project, user, client, "o/secret")
    with pytest.raises(RepositoryNotFound, match="no public repositories"):
        run(add_project, user, client, "o")
    settings.PRIVATE_REPOSITORIES = True
    assert run(add_project, user, client, "o/secret").is_private


def test_private_repositories_are_not_suggested(user):  # noqa: F811
    from community_insights.github import reads

    async def graphql(query, **variables):
        nodes = [
            {"nameWithOwner": "me/open", "stargazerCount": 1, "isPrivate": False},
            {"nameWithOwner": "me/secret", "stargazerCount": 1, "isPrivate": True},
        ]
        empty = {"nodes": []}
        return {
            "viewer": {
                "organizations": empty,
                "repositories": {"nodes": nodes},
                "repositoriesContributedTo": empty,
            }
        }

    names = [s["name"] for s in run(reads.suggestions, graphql)]
    assert names == ["me/open"]


def test_add_source_returns_to_known_pages_only(world, signed_in, monkeypatch):  # noqa: F811
    monkeypatch.setattr(
        "community_insights.github.Client", lambda token: FakeClient(repositories=[repo("n/new")])
    )
    pk = world["project"].pk
    response = signed_in.post(f"/s/{pk}/add/", {"target": "n/new", "page": "admin:index"})
    new = Project.objects.get(target="n/new")
    assert response["Location"] == f"/s/{pk}-{new.pk}/"
    response = signed_in.post(f"/s/{pk}/add/", {"target": "not valid/x/y"})
    assert response["Location"] == f"/s/{pk}/"
