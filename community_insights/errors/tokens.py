"""Errors of GitHub tokens and the access to GitHub."""

from django.utils.translation import gettext_lazy as _

from .github import GitHubError


class TokenError(GitHubError):
    """A problem with a GitHub token or the access to GitHub."""

    title = _("Problem with a token")


class NoGitHubAccess(TokenError):
    """There is no way to read GitHub yet.

    Link your GitHub account or add a personal access token on the page
    *GitHub access*. See *How-to: Add GitHub tokens*.
    """

    title = _("No GitHub access")


class InvalidAPIToken(TokenError):
    """GitHub does not accept the token.

    The token is wrong, was revoked, or belongs to an account that was
    deleted. Create a new token on GitHub and add it on the page *GitHub
    access*; delete the old one there. If it is your linked GitHub account,
    sign out and sign in with GitHub again.
    """

    title = _("Invalid API token")


class ExpiredAPIToken(TokenError):
    """The token has expired.

    Tokens with an expiration date stop working on that date. Create a new
    token on GitHub, or regenerate this one, and add it on the page *GitHub
    access*. The page warns you 14 days before a token expires.
    """

    title = _("Expired API token")


class TokenLifetimeRefused(TokenError):
    """An organisation refuses the token because it is valid for too long.

    Some organisations, such as Plone, do not allow fine-grained tokens that
    never expire or live longer than they allow. Create a token with an
    expiration date within the limit the message names, and add it on the page
    *GitHub access*.
    """

    title = _("Token refused: it lives too long")


class TokenNotAllowed(TokenError):
    """The token may not read this.

    The token lacks a permission, or the organisation does not allow tokens
    or needs to approve it. For a fine-grained token give read access to
    *Pull requests*, *Issues* and *Metadata* and choose the organisation as
    the resource owner; an owner of the organisation may have to approve it.
    """

    title = _("Token not allowed")
