"""Projects of a user with their repositories."""

import factory

from community_insights.models import Project

from .repository import RepositoryFactory
from .user import UserFactory


class ProjectFactory(factory.django.DjangoModelFactory):
    """A project of a new user, with one repository; ``repositories=[...]`` names others."""

    class Meta:
        """The model and how factory_boy makes it."""

        model = Project
        skip_postgeneration_save = True

    user = factory.SubFactory(UserFactory)
    target = factory.Sequence(lambda n: f"owner/repo{n}")

    @factory.post_generation
    def repositories(self, create, chosen, **kwargs):
        """Add the chosen repositories, else the one of the target.

        Args:
            create: False when the project is only built, not saved.
            chosen: The repositories a test named, or None.
            **kwargs: Not used.
        """
        if not create:
            return
        self.repositories.add(*(chosen or [RepositoryFactory(full_name=self.target)]))
