"""The factories of the test data fill what a test does not name."""

import pytest

from community_insights.models import FetchJob
from tests.factories import (
    AccessTokenFactory,
    FetchJobFactory,
    ProjectFactory,
    RepositoryFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db


def test_users_are_numbered_and_have_a_password():
    """Two users differ and can sign in with "pw"."""
    first, second = UserFactory(), UserFactory()
    assert first.username != second.username
    assert first.check_password("pw")
    assert first.email == f"{first.username}@example.org"


def test_a_named_user_is_made_once():
    """The same name gives the same user."""
    assert UserFactory(username="kim") == UserFactory(username="kim")


def test_a_repository_has_its_owner():
    """The owner is the first part of the name."""
    repository = RepositoryFactory(full_name="pycal/icalendar")
    assert repository.owner_login == "pycal"
    assert repository.fetched_at is not None


def test_a_project_has_the_repository_of_its_target():
    """Without chosen repositories, the target is the repository."""
    project = ProjectFactory(target="o/r")
    assert [r.full_name for r in project.repositories.all()] == ["o/r"]


def test_a_project_takes_chosen_repositories():
    """Chosen repositories replace the one of the target."""
    a, b = RepositoryFactory(), RepositoryFactory()
    project = ProjectFactory(target="o", repositories=[a, b])
    assert set(project.repositories.all()) == {a, b}


def test_a_built_project_is_not_saved():
    """build() makes no rows, also no repositories."""
    project = ProjectFactory.build()
    assert project.pk is None


def test_a_token_belongs_to_the_login_of_its_user():
    """The login on GitHub is the name of the user."""
    token = AccessTokenFactory(user=UserFactory(username="kim"))
    assert token.login == "kim"
    assert token.token


def test_a_fetch_job_waits_in_the_queue():
    """A new job is queued for a new repository."""
    job = FetchJobFactory(repository__full_name="o/r")
    assert job.status == FetchJob.QUEUED
    assert job.repository.full_name == "o/r"
