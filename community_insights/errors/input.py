"""Errors in what people enter in forms."""

from django.utils.translation import gettext_lazy as _

from .base import CommunityError


class InvalidInput(CommunityError):
    """A value in a form is not valid.

    The message says which one. Correct it and send the form again.

    This is the base of the errors of forms: only its subclasses are raised,
    and each of them links the page of the documentation about its field.
    """

    title = _("Invalid input")
    guide = ""  # each kind of input has its own page: see the subclasses
    guide_title = ""


class InvalidTarget(InvalidInput):
    """The text is no repository and no organisation.

    Enter a repository as ``owner/name``, such as ``django/django``, or an
    organisation or user as ``owner``, such as ``plone``. A GitHub address like
    ``https://github.com/django/django`` works, too.

    How to add projects: :doc:`/how-to/use`.
    """

    title = _("Not a repository or organisation")
    guide = "how-to/use.html#add-projects"
    guide_title = _("How to add projects")


class InvalidLimit(InvalidInput):
    """A limit of API points must be a whole number above 0.

    Leave the field empty for no limit, where that is allowed.

    API points and limits: :doc:`/how-to/tokens`.
    """

    title = _("Invalid limit")
    guide = "how-to/tokens.html#points-and-limits"
    guide_title = _("API points and limits")


class FetchLimitRequired(InvalidInput):
    """This fetch needs a limit of API points.

    A fetch that is estimated to use more points than the suggested limit of
    your profile (5000 at first, the points one GitHub account has per hour;
    5000 for visitors) needs a limit, so it does not use up your tokens by
    surprise. Enter a limit; what is read until it is reached is kept, and you
    can read the rest later. The suggested limit is set on the page *GitHub
    access* under *Profile*.

    API points and limits: :doc:`/how-to/tokens`.
    """

    title = _("Please set a limit")
    guide = "how-to/tokens.html#points-and-limits"
    guide_title = _("API points and limits")


class InvalidQuery(InvalidInput):
    """The query of the contributors cannot be used.

    A query compares variables with numbers or text, such as
    ``prs_merged >= 2 and days_last < 90`` or ``"berlin" in user_location``, and
    combines them with ``and``, ``or``, ``not`` and parentheses. The message
    says what is wrong; the contributors page lists all variables. Text is
    compared with ``==``, ``!=``, ``in`` and ``not in``, in any case.

    How to write a query: :doc:`/how-to/queries`; the parts of a query:
    :doc:`/reference/query-operators`.
    """

    title = _("Invalid query")
    guide = "reference/query-operators.html"
    guide_title = _("The parts of a query")


class InvalidDateRange(InvalidInput):
    """The dates of the time range cannot be used.

    Enter dates as year-month-day, such as ``2026-01-31``; the first date must
    be before the second. Leave a date empty to start at the beginning or to
    end today.

    The time range: :doc:`/how-to/queries`.
    """

    title = _("Invalid time range")
    guide = "how-to/queries.html#time-range"
    guide_title = _("The time range")


class MissingToken(InvalidInput):
    """No token was entered.

    Paste the token you created on GitHub. See :doc:`/how-to/tokens`.
    """

    title = _("No token entered")
    guide = "how-to/tokens.html"
    guide_title = _("How to add GitHub tokens")


class QueryNotReadable(InvalidQuery):
    """The query is no expression.

    Check the parentheses and the quotes: text is written in quotes, such as
    ``"berlin" in user_location``; words are combined with ``and``, ``or`` and ``not``.

    How to write a query: :doc:`/how-to/queries`; the parts of a query:
    :doc:`/reference/query-operators`.
    """

    title = _("The query cannot be read")
    guide = "reference/query-operators.html"
    guide_title = _("The parts of a query")


class UnknownVariable(InvalidQuery):
    """A name in the query, the sorting or the columns is no variable.

    The message names the variables that are close. All variables are listed
    under *Variables* on the contributors page.

    How to write a query: :doc:`/how-to/queries`; the variables of queries:
    :doc:`/reference/query-variables`.
    """

    title = _("Unknown variable")
    guide = "reference/query-variables.html"
    guide_title = _("The variables of queries")


class NotAComparison(InvalidQuery):
    """A part of the query compares nothing.

    Each part compares a variable with a number or text, such as
    ``prs_merged >= 2``; only the true-or-false variables such as ``user_bot`` stand
    alone. Calculations and functions
    are not possible.

    How to write a query: :doc:`/how-to/queries`; the parts of a query:
    :doc:`/reference/query-operators`.
    """

    title = _("Not a comparison")
    guide = "reference/query-operators.html"
    guide_title = _("The parts of a query")


class NotAValue(InvalidQuery):
    """A side of a comparison is no variable, number or text.

    Calculations such as ``prs_reviewed + comments_total`` and functions cannot be used;
    compare a variable with a number or text in quotes.

    How to write a query: :doc:`/how-to/queries`; the parts of a query:
    :doc:`/reference/query-operators`.
    """

    title = _("Not a variable, number or text")
    guide = "reference/query-operators.html"
    guide_title = _("The parts of a query")


class UnsupportedComparison(InvalidQuery):
    """The query uses a comparison that is not possible.

    Numbers are compared with ``==``, ``!=``, ``<``, ``<=``, ``>`` and ``>=``;
    text with ``==``, ``!=``, ``in`` and ``not in``. ``is`` cannot be used.

    How to write a query: :doc:`/how-to/queries`; the parts of a query:
    :doc:`/reference/query-operators`.
    """

    title = _("Unsupported comparison")
    guide = "reference/query-operators.html"
    guide_title = _("The parts of a query")


class TextComparedWithNumber(InvalidQuery):
    """The query compares text with a number.

    Compare a text variable such as ``user_location`` with text in quotes, and a
    number variable such as ``prs_reviewed`` with a number.

    How to write a query: :doc:`/how-to/queries`; the parts of a query:
    :doc:`/reference/query-operators`.
    """

    title = _("Text compared with a number")
    guide = "reference/query-operators.html"
    guide_title = _("The parts of a query")


class WrongOperatorForText(InvalidQuery):
    """The comparison does not fit text or numbers.

    Text is compared with ``==``, ``!=``, ``in`` and ``not in``; numbers with
    ``==``, ``!=``, ``<``, ``<=``, ``>`` and ``>=``.

    How to write a query: :doc:`/how-to/queries`; the parts of a query:
    :doc:`/reference/query-operators`.
    """

    title = _("This comparison does not fit")
    guide = "reference/query-operators.html"
    guide_title = _("The parts of a query")


class UnknownGroup(InvalidQuery):
    """The contributors cannot be grouped like this.

    Group them by ``user_class``, ``user_association``, ``user_location``,
    ``user_country``, ``user_horizon_europe`` or ``user_bot``, or not at all.

    How to write a query: :doc:`/how-to/queries`; the groups of queries:
    :ref:`group-by`.
    """

    title = _("Unknown group")
    guide = "reference/queries.html#group-by"
    guide_title = _("The groups of queries")


class InvalidDays(InvalidDateRange):
    """The number of the last days of the time range cannot be used.

    Enter a whole number of days above 0, such as ``30`` for the last 30 days,
    or leave the field empty.

    The time range: :ref:`time-range`.
    """

    title = _("Invalid number of days")
    guide = "how-to/queries.html#time-range"
    guide_title = _("The time range")


class InvalidDate(InvalidDateRange):
    """A date of the time range cannot be read.

    Write it as year-month-day, such as ``2026-01-31``, or leave it empty.

    The time range: :doc:`/how-to/queries`.
    """

    title = _("Invalid date")
    guide = "how-to/queries.html#time-range"
    guide_title = _("The time range")


class DatesInWrongOrder(InvalidDateRange):
    """The time range ends before it starts.

    The first date (From) must be before the second (To).

    The time range: :doc:`/how-to/queries`.
    """

    title = _("The dates are in the wrong order")
    guide = "how-to/queries.html#time-range"
    guide_title = _("The time range")


class LimitNotANumber(InvalidLimit):
    """A limit is no whole number.

    Enter digits only, such as ``5000``, or leave the field empty where no
    limit is allowed.

    API points and limits: :doc:`/how-to/tokens`.
    """

    title = _("The limit is no number")
    guide = "how-to/tokens.html#points-and-limits"
    guide_title = _("API points and limits")


class LimitTooSmall(InvalidLimit):
    """A limit is below 1.

    A limit of API points is at least 1. Leave the field empty for no limit,
    where that is allowed.

    API points and limits: :doc:`/how-to/tokens`.
    """

    title = _("The limit is too small")
    guide = "how-to/tokens.html#points-and-limits"
    guide_title = _("API points and limits")


class InvalidPercentage(InvalidInput):
    """A slider of a token is not between 0 and 100.

    The sliders of a token are percentages: whole numbers from 0 to 100.

    How to add GitHub tokens: :doc:`/how-to/tokens`.
    """

    title = _("Invalid percentage")
    guide = "how-to/tokens.html#share-points"
    guide_title = _("How to add GitHub tokens")


class InvalidExtraPoints(InvalidInput):
    """The points allowed for this hour are not a whole number above 0.

    Enter how many more points of your tokens are fine this hour, such as
    ``500``.

    API points and limits: :doc:`/how-to/tokens`.
    """

    title = _("Invalid number of points")
    guide = "how-to/tokens.html#points-and-limits"
    guide_title = _("API points and limits")


class UnknownRuleKind(InvalidInput):
    """A rule of a class of people has a kind that does not exist.

    Choose the kind of a rule from the list of the form: handles, pattern,
    status, bot, location or everybody.

    Classes of people: :doc:`/reference/classes`.
    """

    title = _("Unknown kind of rule")
    guide = "reference/classes.html"
    guide_title = _("Classes of people")


class InvalidHandle(InvalidInput):
    """The text is no GitHub handle.

    A handle has letters, digits and single hyphens, at most 39 characters, such
    as ``coveralls``. Use the button of a suggestion on the page *Classes*, or
    add the handle to a rule of the kind *handles*.

    Classes of people: :doc:`/reference/classes`.
    """

    title = _("Not a GitHub handle")
    guide = "reference/classes.html"
    guide_title = _("Classes of people")


class NoBotClass(InvalidInput):
    """No class of people has the rule "is a bot", so a bot cannot be added.

    Add the rule *is a bot* to the class for bots on the page *Classes*, or
    create a class with it. Then add the bot again.

    Classes of people: :doc:`/reference/classes`.
    """

    title = _("No class for bots")
    guide = "reference/classes.html"
    guide_title = _("Classes of people")


class ClassNameTaken(InvalidInput):
    """You have a class of people with this name already.

    The names of your classes are different, so that a badge and a query can
    name one. Choose another name, or change the class that has it.

    Classes of people: :doc:`/reference/classes`.
    """

    title = _("Class name taken")
    guide = "reference/classes.html"
    guide_title = _("Classes of people")


class PresetClassNotDeleted(InvalidInput):
    """A class of people the site made cannot be deleted, only hidden.

    The classes *bot*, *collaborator or higher* and *external* sort everybody
    the site knows. Hide one with its button: it then still decides who belongs
    to it, but the statistics do not show it.

    Classes of people: :doc:`/reference/classes`.
    """

    title = _("Class cannot be deleted")
    guide = "reference/classes.html#default-classes"
    guide_title = _("Classes of people")


class UnknownClasses(InvalidInput):
    """An address names classes of people that do not exist.

    A shared statistic names the classes it was made with, such as
    ``classes=maintainer-3+bot-1``. One of them was deleted, or the address was
    changed. The page shows your own classes instead.

    Classes of people: :doc:`/reference/classes`.
    """

    title = _("Unknown classes")
    guide = "reference/classes.html#shared-statistics"
    guide_title = _("Classes of people")


class InvalidColor(InvalidInput):
    """The colour of a class is no colour like ``#649568``.

    Choose the colour with the colour field of the class; it is written as
    ``#`` and six hexadecimal digits.

    Classes of people: :doc:`/reference/classes`.
    """

    title = _("Invalid colour")
    guide = "reference/classes.html"
    guide_title = _("Classes of people")


class InvalidClassOrder(InvalidInput):
    """The new order of the classes does not name each of your classes once.

    The page was probably changed in another window. Load the page *Classes*
    again and move the class once more.

    Classes of people: :doc:`/reference/classes`.
    """

    title = _("Invalid order of the classes")
    guide = "reference/classes.html"
    guide_title = _("Classes of people")


class InvalidTokenOrder(InvalidInput):
    """The new order of the tokens does not name each of your tokens once.

    The page was probably changed in another window. Load the page *GitHub access*
    again and move the token once more.

    Tokens and the order they are used in: :doc:`/how-to/tokens`.
    """

    title = _("Invalid order of the tokens")
    guide = "how-to/tokens.html"
    guide_title = _("How to add GitHub tokens")


class UnknownTable(InvalidInput):
    """There is no table of that name to download.

    The tables are responses, items, events, commits and contributors, as CSV,
    JSON or ODS. Use the links of *Data and sources* on a statistics page.

    Check the numbers yourself: :doc:`/how-to/verify`.
    """

    title = _("Unknown table")
    guide = "how-to/verify.html"
    guide_title = _("Check the numbers yourself")
