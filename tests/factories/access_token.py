"""Tokens of GitHub that people added."""

import factory

from community_insights.models import AccessToken

from .user import UserFactory


class AccessTokenFactory(factory.django.DjangoModelFactory):
    """A token of a new user, with the login of the user on GitHub."""

    class Meta:
        """The model and how factory_boy makes it."""

        model = AccessToken

    user = factory.SubFactory(UserFactory)
    token = factory.Sequence(lambda n: f"token{n}")
    login = factory.LazyAttribute(lambda token: token.user.username)
