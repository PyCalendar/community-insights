"""Adding, renaming and removing projects; only public repositories."""

import pytest

from community_insights.errors import InvalidTarget
from community_insights.models import Project
from community_insights.sync import add_project

from ..fakes import FakeClient, repo, run

pytestmark = pytest.mark.django_db


def test_add_project_owner_and_repo(user):
    """Add project owner and repo."""
    client = FakeClient(repositories=[repo("o/a", 9), repo("o/b", 1, private=True)])
    project = run(add_project, user, client, "o")
    # for now only public repositories: the private one of the organisation is skipped
    assert project.is_owner and project.repositories.count() == 1 and not project.is_private
    single = run(add_project, user, client, "https://github.com/o/a")
    assert single.target == "o/a" and single.repositories.count() == 1
    with pytest.raises(InvalidTarget):
        run(add_project, user, client, "a/b/c")


def test_rename_a_project(world, signed_in):  # noqa: F811
    """Rename a project."""
    pk = world["project"].pk
    signed_in.post(f"/projects/{pk}/rename/", {"name": "Our tool"})
    assert Project.objects.get(pk=pk).label == "Our tool"
    page = signed_in.get(f"/s/{pk}/").content.decode()
    assert "Our tool" in page
    signed_in.post(f"/projects/{pk}/rename/", {"name": "  "})
    assert Project.objects.get(pk=pk).label == "o/r"
    assert signed_in.get(f"/projects/{pk}/rename/").status_code == 405


def test_private_repositories_are_refused_for_now(user, settings):  # noqa: F811
    """Private repositories are refused for now."""
    from community_insights.errors import PrivateRepositoryRefused, RepositoryNotFound

    client = FakeClient(repositories=[repo("o/secret", private=True)])
    with pytest.raises(PrivateRepositoryRefused):
        run(add_project, user, client, "o/secret", own=client)  # their own token sees it
    with pytest.raises(RepositoryNotFound, match="no public repositories"):
        run(add_project, user, client, "o", own=client)
    settings.PRIVATE_REPOSITORIES = True
    assert run(add_project, user, client, "o/secret", own=client).is_private


def test_a_private_repository_only_others_see_is_not_found(user, settings):
    """Tokens shared by others never tell that a private repository of somebody exists."""
    from community_insights.errors import RepositoryNotFound

    others = FakeClient(repositories=[repo("o/secret", private=True), repo("o/open")])
    mine = FakeClient(repositories=[repo("o/open")], hidden={"o/secret"})  # cannot see it
    for own in (mine, None):
        with pytest.raises(RepositoryNotFound, match="was not found"):
            run(add_project, user, others, "o/secret", own=own)
    settings.PRIVATE_REPOSITORIES = True
    with pytest.raises(RepositoryNotFound, match="was not found"):
        run(add_project, user, others, "o/secret", own=mine)
    project = run(add_project, user, others, "o", own=mine)
    assert [r.full_name for r in project.repositories.all()] == ["o/open"]
    assert not project.is_private


def test_the_dashboard_does_not_tell_of_private_repositories_of_others(
    user, signed_in, monkeypatch
):
    """The dashboard does not tell of private repositories of others."""
    from django.contrib.auth import get_user_model

    from community_insights.models import AccessToken

    other = get_user_model().objects.create_user("kim", "kim@example.org", "pw")
    AccessToken.objects.create(user=other, token="kims", login="kim", shared_percent=50)
    AccessToken.objects.filter(user=user).delete()
    fake = FakeClient(repositories=[repo("kim/secret", private=True)])
    monkeypatch.setattr("community_insights.github.Client", lambda token: fake)
    from allauth.socialaccount.models import SocialToken

    SocialToken.objects.all().delete()  # no linked account that could see it
    page = signed_in.post("/dashboard/", {"target": "kim/secret"}, follow=True).content.decode()
    assert "was not found" in page
    assert "Private repositories" not in page and "is private" not in page
    assert not Project.objects.filter(target="kim/secret").exists()


def test_private_repositories_are_not_suggested(user):  # noqa: F811
    """Private repositories are not suggested."""
    from community_insights.github import reads

    async def graphql(query, **variables):
        """Answer with a public and a private repository."""
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
    """Add source returns to known pages only."""
    monkeypatch.setattr(
        "community_insights.github.Client", lambda token: FakeClient(repositories=[repo("n/new")])
    )
    pk = world["project"].pk
    response = signed_in.post(f"/s/{pk}/add/", {"target": "n/new", "page": "admin:index"})
    new = Project.objects.get(target="n/new")
    assert response["Location"] == f"/s/{pk}-{new.pk}/"
    response = signed_in.post(f"/s/{pk}/add/", {"target": "not valid/x/y"})
    assert response["Location"] == f"/s/{pk}/"
