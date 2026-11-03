"""Tokens of GitHub that people added."""

import factory

from community_insights.models import AccessToken, TokenGrant

from .user import UserFactory


class AccessTokenFactory(factory.django.DjangoModelFactory):
    """A token of a new user, with the login of the user on GitHub."""

    class Meta:
        """The model and how factory_boy makes it."""

        model = AccessToken

    user = factory.SubFactory(UserFactory)
    token = factory.Sequence(lambda n: f"token{n}")
    login = factory.LazyAttribute(lambda token: token.user.username)

    @factory.post_generation
    def shared_percent(self, create, extracted, **kwargs):
        """The share for everybody on this site: a grant, 10 %% by default as for a new token.

        Args:
            create: Whether the token was saved.
            extracted: The percent given; None for 10, 0 for no grant.
            **kwargs: Not used.
        """
        percent = 10 if extracted is None else extracted
        if create and percent:
            share(self, percent)


def share(token: AccessToken, percent: int) -> TokenGrant:
    """Share a token with everybody on this site, as the slider on GitHub access does.

    Args:
        token: The token.
        percent: Its share for everybody, of its maximum.

    Returns:
        The grant.
    """
    return TokenGrant.objects.create(token=token, kind=TokenGrant.EVERYBODY, percent=percent)
