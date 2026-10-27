"""Errors of GitHub and of reaching it."""

from datetime import datetime

from django.utils.translation import gettext_lazy as _

from .base import CommunityError


class GitHubError(CommunityError):
    """GitHub answered with an error.

    The message contains what GitHub said. Try again later; if it stays,
    report a bug.

    How to report a bug: :doc:`/how-to/report-bug`.
    """

    title = _("GitHub reported an error")
    guide = "how-to/report-bug.html"
    guide_title = _("How to report a bug")


class GitHubUnreachable(GitHubError):
    """GitHub cannot be reached.

    The server of this site cannot connect to GitHub, or GitHub did not answer
    in time. Check https://www.githubstatus.com/ and try again later. If you run
    this site, check the network and the ``GITHUB_API`` setting.

    The settings of the site: :doc:`/reference/configuration`.
    """

    title = _("GitHub cannot be reached")
    guide = "reference/configuration.html"
    guide_title = _("The settings of the site")


class RepositoryNotFound(GitHubError):
    """The repository or organisation does not exist, or the token cannot see it.

    Check the spelling. A private repository can only be read with a token of
    somebody who can see it: for a fine-grained token, the repository must be
    selected and *Pull requests*, *Issues* and *Metadata* must be readable.
    Use *Test on my projects* on the page *GitHub access* to see which
    repositories a token can read.

    How to add GitHub tokens: :doc:`/how-to/tokens`.
    """

    title = _("Not found on GitHub")
    guide = "how-to/tokens.html"
    guide_title = _("How to add GitHub tokens")


class OwnerNotFound(RepositoryNotFound):
    """The organisation or user does not exist on GitHub.

    Check the spelling of the name: it is the part of a GitHub address after
    ``github.com/``, such as ``plone`` in ``https://github.com/plone``.

    How to add projects: :doc:`/how-to/use`.
    """

    title = _("Organisation or user not found")
    guide = "how-to/use.html#add-projects"
    guide_title = _("How to add projects")


class NoPublicRepositories(RepositoryNotFound):
    """The organisation or user has no public repositories.

    For now only public repositories are read. Add an organisation or user
    with public repositories, or one repository of it.

    How to add projects: :doc:`/how-to/use`.
    """

    title = _("No public repositories")
    guide = "how-to/use.html#add-projects"
    guide_title = _("How to add projects")


class GitHubRequestRejected(GitHubError):
    """GitHub refused the request as it was sent.

    This is likely a bug of this site, or GitHub changed its API. Please report
    it with "Report a bug" and include the message.

    How to report a bug: :doc:`/how-to/report-bug`.
    """

    title = _("GitHub refused the request")
    guide = "how-to/report-bug.html"
    guide_title = _("How to report a bug")


class GitHubAnswerNotJSON(GitHubError):
    """GitHub answered with something this site cannot read.

    This happens when GitHub has problems and sends an error page. Try again
    later; see https://www.githubstatus.com/.

    How to report a bug: :doc:`/how-to/report-bug`.
    """

    title = _("GitHub answered something unreadable")
    guide = "how-to/report-bug.html"
    guide_title = _("How to report a bug")


class GraphQLError(GitHubError):
    """GitHub could not answer a query of its GraphQL API.

    The message says what GitHub reported. If it stays, please report a bug
    with "Report a bug".

    How to report a bug: :doc:`/how-to/report-bug`.
    """

    title = _("GitHub could not answer the query")
    guide = "how-to/report-bug.html"
    guide_title = _("How to report a bug")


class PrivateRepositoryRefused(GitHubError):
    """Private repositories are not supported yet.

    For now, Contributor Community Insights reads public repositories only: the
    statistics, badges and downloads of a private repository could show what
    should stay private. Add a public repository or organisation instead; of an
    organisation, only the public repositories are read.

    This error only comes when a token of your own can see the repository.
    Tokens that others share, or donated to the site, never tell that a private
    repository of somebody else exists: it is then not found.

    How to add projects: :doc:`/how-to/use`.
    """

    title = _("Private repositories are not supported yet")
    guide = "how-to/use.html#add-projects"
    guide_title = _("How to add projects")


class RateLimitExceeded(GitHubError):
    """The rate limit of a token is used up.

    GitHub allows 5000 API points per hour for each account. The token is
    used again when GitHub renews its points; until then the next token is
    used. Add more tokens to read faster, see :doc:`/how-to/tokens`.
    """

    title = _("Rate limit used up")
    guide = "how-to/tokens.html#points-and-limits"
    guide_title = _("API points and limits")

    def __init__(self, detail: str = "", reset_at: datetime | None = None, **context):
        """GitHub says the points of the token are used up.

        Args:
            detail: What happened.
            reset_at: When GitHub renews the points.
            **context: More about it.
        """
        super().__init__(detail, **context)
        self.reset_at = reset_at


class SecondaryRateLimitExceeded(RateLimitExceeded):
    """GitHub asks to slow down: a secondary rate limit was hit.

    Besides the points per hour, GitHub limits how many requests run at the
    same time and how many points are used per minute. The site waits as long
    as GitHub asks (``retry-after``) and tries again; for longer waits it uses
    the next token. Nothing needs to be done; reading many repositories at the
    same time takes longer then.

    API points and limits: :doc:`/how-to/tokens`.
    """

    title = _("GitHub asks to slow down")
    guide = "how-to/tokens.html#points-and-limits"
    guide_title = _("API points and limits")

    def __init__(self, detail: str = "", retry_after: float | None = None, **context):
        """GitHub asks to slow down.

        Args:
            detail: What happened.
            retry_after: The seconds GitHub asks to wait, None if it did not say.
            **context: More about it.
        """
        super().__init__(detail, **context)
        self.retry_after = retry_after
