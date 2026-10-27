"""Errors in what people enter in forms."""

from django.utils.translation import gettext_lazy as _

from .base import CommunityError


class InvalidInput(CommunityError):
    """A value in a form is not valid.

    The message says which one. Correct it and send the form again.
    """

    title = _("Invalid input")


class InvalidTarget(InvalidInput):
    """The text is no repository and no organisation.

    Enter a repository as ``owner/name``, such as ``django/django``, or an
    organisation or user as ``owner``, such as ``plone``. A GitHub address like
    ``https://github.com/django/django`` works, too.
    """

    title = _("Not a repository or organisation")


class InvalidLimit(InvalidInput):
    """A limit of API points must be a whole number above 0.

    Leave the field empty for no limit, where that is allowed.
    """

    title = _("Invalid limit")


class FetchLimitRequired(InvalidInput):
    """This fetch needs a limit of API points.

    A fetch that is estimated to use more than 5000 points, the points one
    GitHub account has per hour, needs a limit, so it does not use up your
    tokens by surprise. Enter a limit; what is read until it is reached is
    kept, and you can read the rest later. The suggested limit can be changed
    on the page *GitHub access* under *Profile*.
    """

    title = _("Please set a limit")


class InvalidQuery(InvalidInput):
    """The query of the contributors cannot be used.

    A query compares variables with numbers or text, such as
    ``prs_merged >= 2 and days_last < 90`` or ``"berlin" in location``, and
    combines them with ``and``, ``or``, ``not`` and parentheses. The message
    says what is wrong; the contributors page lists all variables. Text is
    compared with ``==``, ``!=``, ``in`` and ``not in``, in any case.
    """

    title = _("Invalid query")


class InvalidDateRange(InvalidInput):
    """The dates of the time range cannot be used.

    Enter dates as year-month-day, such as ``2026-01-31``; the first date must
    be before the second. Leave a date empty to start at the beginning or to
    end today.
    """

    title = _("Invalid time range")


class MissingToken(InvalidInput):
    """No token was entered.

    Paste the token you created on GitHub. See *How-to: Add GitHub tokens* in
    the documentation.
    """

    title = _("No token entered")


class QueryNotReadable(InvalidQuery):
    """The query is no expression.

    Check the parentheses and the quotes: text is written in quotes, such as
    ``"berlin" in location``; words are combined with ``and``, ``or`` and ``not``.
    """

    title = _("The query cannot be read")


class UnknownVariable(InvalidQuery):
    """A name in the query, the sorting or the columns is no variable.

    The message names the variables that are close. All variables are listed
    under *Variables* on the contributors page.
    """

    title = _("Unknown variable")


class NotAComparison(InvalidQuery):
    """A part of the query compares nothing.

    Each part compares a variable with a number or text, such as
    ``prs_merged >= 2``; only ``bot`` stands alone. Calculations and functions
    are not possible.
    """

    title = _("Not a comparison")


class NotAValue(InvalidQuery):
    """A side of a comparison is no variable, number or text.

    Calculations such as ``reviews + comments`` and functions cannot be used;
    compare a variable with a number or text in quotes.
    """

    title = _("Not a variable, number or text")


class UnsupportedComparison(InvalidQuery):
    """The query uses a comparison that is not possible.

    Numbers are compared with ``==``, ``!=``, ``<``, ``<=``, ``>`` and ``>=``;
    text with ``==``, ``!=``, ``in`` and ``not in``. ``is`` cannot be used.
    """

    title = _("Unsupported comparison")


class TextComparedWithNumber(InvalidQuery):
    """The query compares text with a number.

    Compare a text variable such as ``location`` with text in quotes, and a
    number variable such as ``reviews`` with a number.
    """

    title = _("Text compared with a number")


class WrongOperatorForText(InvalidQuery):
    """The comparison does not fit text or numbers.

    Text is compared with ``==``, ``!=``, ``in`` and ``not in``; numbers with
    ``==``, ``!=``, ``<``, ``<=``, ``>`` and ``>=``.
    """

    title = _("This comparison does not fit")


class UnknownGroup(InvalidQuery):
    """The contributors cannot be grouped like this.

    Group them by ``class``, ``location`` or ``bot``, or not at all.
    """

    title = _("Unknown group")


class InvalidDate(InvalidDateRange):
    """A date of the time range cannot be read.

    Write it as year-month-day, such as ``2026-01-31``, or leave it empty.
    """

    title = _("Invalid date")


class DatesInWrongOrder(InvalidDateRange):
    """The time range ends before it starts.

    The first date (From) must be before the second (To).
    """

    title = _("The dates are in the wrong order")


class LimitNotANumber(InvalidLimit):
    """A limit is no whole number.

    Enter digits only, such as ``5000``, or leave the field empty where no
    limit is allowed.
    """

    title = _("The limit is no number")


class LimitTooSmall(InvalidLimit):
    """A limit is below 1.

    A limit of API points is at least 1. Leave the field empty for no limit,
    where that is allowed.
    """

    title = _("The limit is too small")


class InvalidPercentage(InvalidInput):
    """A slider of a token is not between 0 and 100.

    The sliders of a token are percentages: whole numbers from 0 to 100.
    """

    title = _("Invalid percentage")


class InvalidExtraPoints(InvalidInput):
    """The points allowed for this hour are not a whole number above 0.

    Enter how many more points of your tokens are fine this hour, such as
    ``500``.
    """

    title = _("Invalid number of points")


class UnknownRuleKind(InvalidInput):
    """A rule of a class of people has a kind that does not exist.

    Choose the kind of a rule from the list of the form: handles, pattern,
    status, bot, location or everybody.
    """

    title = _("Unknown kind of rule")


class UnknownTable(InvalidInput):
    """There is no table of that name to download.

    The tables are responses, items, events, commits and contributors, as CSV,
    JSON or ODS. Use the links of *Data and sources* on a statistics page.
    """

    title = _("Unknown table")
