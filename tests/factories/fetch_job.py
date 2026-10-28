"""Fetches of a repository, waiting in the queue."""

import factory

from community_insights.models import FetchJob

from .repository import RepositoryFactory
from .user import UserFactory


class FetchJobFactory(factory.django.DjangoModelFactory):
    """A queued fetch of a new repository by a new user."""

    class Meta:
        """The model and how factory_boy makes it."""

        model = FetchJob

    user = factory.SubFactory(UserFactory)
    repository = factory.SubFactory(RepositoryFactory)
    status = FetchJob.QUEUED
