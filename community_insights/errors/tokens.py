"""Errors of GitHub tokens and the access to GitHub."""

from django.utils.translation import gettext_lazy as _

from .github import GitHubError


class TokenError(GitHubError):
    """A problem with a GitHub token or the access to GitHub.

    How to add GitHub tokens: :doc:`/how-to/tokens`.
    """

    title = _("Problem with a token")
    guide = "how-to/tokens.html"
    guide_title = _("How to add GitHub tokens")


class NoGitHubAccess(TokenError):
    """There is no way to read GitHub yet.

    Link your GitHub account or add a personal access token on the page
    *GitHub access*. See :doc:`/how-to/tokens`.
    """

    title = _("No GitHub access")
    guide = "how-to/tokens.html"
    guide_title = _("How to add GitHub tokens")


class InvalidAPIToken(TokenError):
    """GitHub does not accept the token.

    The token is wrong, was revoked, or belongs to an account that was
    deleted. Create a new token on GitHub and add it on the page *GitHub
    access*; delete the old one there. If it is your linked GitHub account,
    sign out and sign in with GitHub again.

    How to add GitHub tokens: :doc:`/how-to/tokens`.
    """

    title = _("Invalid API token")
    guide = "how-to/tokens.html"
    guide_title = _("How to add GitHub tokens")


class ExpiredAPIToken(TokenError):
    """The token has expired.

    Tokens with an expiration date stop working on that date. Create a new
    token on GitHub, or regenerate this one, and add it on the page *GitHub
    access*. The page warns you 14 days before a token expires.

    How to add GitHub tokens: :doc:`/how-to/tokens`.
    """

    title = _("Expired API token")
    guide = "how-to/tokens.html"
    guide_title = _("How to add GitHub tokens")


class TokenLifetimeRefused(TokenError):
    """An organisation refuses the token because it is valid for too long.

    Some organisations, such as Plone, do not allow fine-grained tokens that
    never expire or live longer than they allow. Create a token with an
    expiration date within the limit the message names, and add it on the page
    *GitHub access*.

    How to add GitHub tokens: :doc:`/how-to/tokens`.
    """

    title = _("Token refused: it lives too long")
    guide = "how-to/tokens.html"
    guide_title = _("How to add GitHub tokens")


class TokenNotAllowed(TokenError):
    """The token may not read this.

    The token lacks a permission, or the organisation does not allow tokens
    or needs to approve it. For a fine-grained token give read access to
    *Pull requests*, *Issues* and *Metadata* and choose the organisation as
    the resource owner; an owner of the organisation may have to approve it.

    How to add GitHub tokens: :doc:`/how-to/tokens`.
    """

    title = _("Token not allowed")
    guide = "how-to/tokens.html"
    guide_title = _("How to add GitHub tokens")
