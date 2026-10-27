"""The base of all errors."""

from django.utils.translation import gettext_lazy as _

DOCS = "https://community-insights.readthedocs.io/en/latest/"
DOCS_URL = f"{DOCS}reference/errors.html"


class CommunityError(Exception):
    """Something went wrong.

    This is the base of all errors. If you see it, please report a bug with
    "Report a bug" at the bottom of the page.

    How to report a bug: :doc:`/how-to/report-bug`.
    """

    title = _("Something went wrong")
    # a page of the documentation that explains what the error is about, and its link text;
    # "" for none: tests/errors/test_error_classes.py lists the errors that may have none
    guide = "how-to/report-bug.html"
    guide_title = _("How to report a bug")

    def __init__(self, detail: str = "", **context):
        """An error people can meet, with what happened.

        Args:
            detail: What happened, shown after the title; the title if empty.
            **context: More about it, such as the HTTP status.
        """
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
        """The description of this error in the documentation.

        Returns:
            The address of the description.
        """
        return f"{DOCS_URL}#{cls.__module__}.{cls.__name__}"

    @classmethod
    def guide_url(cls) -> str:
        """The page of the documentation that explains what the error is about.

        Returns:
            The address of the page, "" for errors without one.
        """
        return f"{DOCS}{cls.guide}" if cls.guide else ""


class UnexpectedError(CommunityError):
    """An error that this site does not know.

    This is a bug. Please report it with "Report a bug" at the bottom of the
    page and include the message.

    How to report a bug: :doc:`/how-to/report-bug`.
    """

    title = _("Unexpected error")
    guide = "how-to/report-bug.html"
    guide_title = _("How to report a bug")
