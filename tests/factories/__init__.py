"""Test data made by factory_boy: users, repositories, projects, tokens and fetch jobs.

Each factory fills the fields a test does not care about; a test names only what it checks::

    token = AccessTokenFactory(shared_percent=10)
    job = FetchJobFactory(user=token.user, status=FetchJob.RUNNING)
"""

from .access_token import AccessTokenFactory
from .fetch_job import FetchJobFactory
from .project import ProjectFactory
from .repository import RepositoryFactory
from .user import UserFactory

__all__ = [
    "AccessTokenFactory",
    "FetchJobFactory",
    "ProjectFactory",
    "RepositoryFactory",
    "UserFactory",
]
