"""The pages of a project and of a person in it: one list for every menu that offers them."""

from django.urls import reverse
from django.utils.translation import gettext_lazy as _

# the pages of a scope: the name of the address and the title; "compare" only for several
PROJECT_PAGES = [
    ("overview", _("Overview")),
    ("response_times", _("Response times")),
    ("contributors", _("Contributors")),
    ("items", _("Pull requests and issues")),
    ("replies", _("Replies")),
    ("badges", _("Badges")),
    ("compare", _("Compare repositories")),
]

# the pages of a person in a scope
PERSON_PAGES = [
    ("person", _("Contributions")),
    ("person_replies", _("Replies")),
    ("person_items", _("Pull requests and issues")),
    ("reply_badge_share", _("Badges")),
]


def project_pages(scope_text: str, query: str = "", several: bool = True) -> list[tuple]:
    """The pages of a scope, for a menu.

    Args:
        scope_text: The text of the scope, such as ``3`` or ``plone~volto``.
        query: The time range and the classes to keep, such as ``?last=30``.
        several: Whether the scope has several repositories, which can be compared.

    Returns:
        The name, the title and the address of each page.

    Examples:
        >>> [name for name, _, _ in project_pages("o~r", several=False)][-1]
        'badges'
    """
    return [
        (name, title, reverse(name, args=[scope_text]) + query)
        for name, title in PROJECT_PAGES
        if several or name != "compare"
    ]


def person_pages(scope_text: str, login: str, query: str = "") -> list[tuple]:
    """The pages of a person in a scope, for a menu.

    Args:
        scope_text: The text of the scope.
        login: The handle of the person.
        query: The time range and the classes to keep.

    Returns:
        The name, the title and the address of each page.
    """
    return [
        (name, title, reverse(name, args=[scope_text, login]) + query)
        for name, title in PERSON_PAGES
    ]
