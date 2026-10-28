"""Repositories of GitHub, as fetched."""

import factory
from django.utils import timezone

from community_insights.models import Repository


class RepositoryFactory(factory.django.DjangoModelFactory):
    """A repository: owner/repo1, owner/repo2, ..., fetched now."""

    class Meta:
        """The model and how factory_boy makes it."""

        model = Repository
        django_get_or_create = ("full_name",)

    full_name = factory.Sequence(lambda n: f"owner/repo{n}")
    owner_login = factory.LazyAttribute(lambda repository: repository.full_name.split("/")[0])
    fetched_at = factory.LazyFunction(timezone.now)
