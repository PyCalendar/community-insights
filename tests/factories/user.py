"""Users with a password, numbered names and an address."""

import factory
from django.contrib.auth import get_user_model


class UserFactory(factory.django.DjangoModelFactory):
    """A user: user1, user2, ... with the password "pw"."""

    class Meta:
        """The model and how factory_boy makes it."""

        model = get_user_model()
        django_get_or_create = ("username",)
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda user: f"{user.username}@example.org")
    password = factory.django.Password("pw")
