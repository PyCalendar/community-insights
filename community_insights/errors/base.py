"""The base of all errors."""

from django.utils.translation import gettext_lazy as _

DOCS_URL = "https://community-insights.readthedocs.io/en/latest/reference/errors.html"


class CommunityError(Exception):
    """Something went wrong.

    This is the base of all errors. If you see it, please report a bug with
    "Report a bug" at the bottom of the page.
    """

    title = _("Something went wrong")

    def __init__(self, detail: str = "", **context):
        super().__init__(detail or str(self.title))
        self.detail = detail
        self.context = context

    def __str__(self) -> str:
        return self.detail or str(self.title)

    @property
    def code(self) -> str:
        """The name of the error, stored with failed fetches and tokens."""
        return type(self).__name__

    @classmethod
    def docs_url(cls) -> str:
        """The description of this error in the documentation."""
        return f"{DOCS_URL}#{cls.__module__}.{cls.__name__}"


class UnexpectedError(CommunityError):
    """An error that this site does not know.

    This is a bug. Please report it with "Report a bug" at the bottom of the
    page and include the message.
    """

    title = _("Unexpected error")
