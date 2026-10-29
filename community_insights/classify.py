"""Classes of people for response times."""

import re
from fnmatch import fnmatchcase

from django.utils.translation import gettext

from .errors import UnknownClasses
from .models import ClassRule, PersonClass

MEMBERS = ("owner", "member", "collaborator")
# bots with an account like that of a person: GitHub does not mark them as bots
KNOWN_BOTS = ("coveralls",)
# in the palette of the website, told apart by lightness
# (key, name, colour, rules); the key stays when the class is renamed, and names the
# explanation in docs/reference/classes.rst (class-<key>)
DEFAULT_CLASSES = [
    ("bot", "bot", "#9ccc9c", [(ClassRule.BOT, ""), (ClassRule.HANDLE, " ".join(KNOWN_BOTS))]),
    (
        "collaborator",
        "collaborator or higher",
        "#2b5329",
        [(ClassRule.ASSOCIATION, " ".join(MEMBERS))],
    ),
    ("external", "external", "#149414", [(ClassRule.ANY, "")]),
]


def ensure_default_classes(user) -> None:
    """Give a user the default classes (bot, collaborator or higher, external) if they have none.

    Args:
        user: The user.
    """
    if user.classes.exists():
        return
    for key, name, color, rules in DEFAULT_CLASSES:
        person_class = PersonClass.objects.create(user=user, name=name, color=color, preset=key)
        for kind, value in rules:
            person_class.rules.create(kind=kind, value=value)


def bot_class(user) -> PersonClass | None:
    """The first class of a user with the rule "is a bot", None if there is none.

    Args:
        user: The user, or an anonymous one.

    Returns:
        The class.
    """
    return Classifier(user).bot_class()


def add_handle(person_class: PersonClass, login: str) -> ClassRule:
    """Add a handle to the first handle rule of a class, or a new handle rule.

    Args:
        person_class: A saved class.
        login: The GitHub handle.

    Returns:
        The rule with the handle.
    """
    rule = person_class.rules.filter(kind=ClassRule.HANDLE).first()
    if rule is None:
        return person_class.rules.create(kind=ClassRule.HANDLE, value=login)
    if login.lower() not in rule.value.lower().split():
        rule.value = f"{rule.value} {login}".strip()
        rule.save()
    return rule


def rule_matches(
    rule: ClassRule, login: str, association: str, is_bot: bool, location: str
) -> bool:
    """Whether a rule matches an actor: by handle, pattern, status, bot or location, in any case.

    Args:
        rule: The rule.
        login: The handle of the actor.
        association: Their status in the repository, such as ``MEMBER``.
        is_bot: Whether GitHub marks them as a bot.
        location: The location of their profile, "" if unknown.

    Returns:
        True if the rule matches.
    """
    login, association, location = login.lower(), association.lower(), location.lower()
    words = [word.lower() for word in rule.value.replace(",", " ").split()]
    match rule.kind:
        case ClassRule.HANDLE:
            return login in words
        case ClassRule.PATTERN:
            return any(fnmatchcase(login, word) for word in words)
        case ClassRule.ASSOCIATION:
            return association in words
        case ClassRule.BOT:
            return is_bot
        case ClassRule.LOCATION:
            return bool(location) and any(
                fnmatchcase(location, f"*{word.strip('*')}*") for word in words
            )
        case ClassRule.ANY:
            return True
    return False


def classes_of(user) -> list[tuple[PersonClass, list[ClassRule]]]:
    """The classes of people with their rules, in their order.

    Args:
        user: A user, or an anonymous one: visitors get the default classes, made
            in memory and not saved.

    Returns:
        Pairs of a class and its rules.
    """
    if user is None or not user.is_authenticated:
        return [
            (
                PersonClass(name=name, color=color, preset=key),
                [ClassRule(kind=kind, value=value) for kind, value in rules],
            )
            for key, name, color, rules in DEFAULT_CLASSES
        ]
    ensure_default_classes(user)
    found = PersonClass.objects.filter(user=user).prefetch_related("rules")
    return [(person_class, list(person_class.rules.all())) for person_class in found]


IDENT = re.compile(r"^[a-z0-9-]*?-?(\d+)$")


def classes_by_ids(text: str) -> list[PersonClass]:
    """The classes of an address, in their order, of whichever user made them.

    Args:
        text: Their ids, such as ``maintainer-3 bot-1``, separated by spaces or commas.

    Returns:
        The classes, with their rules.

    Raises:
        UnknownClasses: If an id names no class.

    Examples:
        >>> classes_by_ids("")
        []
    """
    idents = [part for part in text.replace(",", " ").split() if part]
    numbers = []
    for ident in idents:
        found = IDENT.match(ident.lower())
        if not found:
            raise UnknownClasses(gettext("%(ident)s is no id of a class.") % {"ident": repr(ident)})
        numbers.append(int(found.group(1)))
    known = PersonClass.objects.filter(pk__in=numbers).prefetch_related("rules").in_bulk()
    missing = [ident for ident, pk in zip(idents, numbers, strict=True) if pk not in known]
    if missing:
        raise UnknownClasses(
            gettext("There are no classes %(idents)s.") % {"idents": ", ".join(missing)}
        )
    return [known[pk] for pk in numbers]


def differs_from_default(user) -> bool:
    """Whether the classes of a user differ from the ones every account starts with.

    Args:
        user: A user, or an anonymous one.

    Returns:
        True if a name, colour, rule, the order or whether one is hidden differs.
    """
    if user is None or not user.is_authenticated:
        return False
    found = [
        (c.name, c.color, c.hidden, sorted((r.kind, r.value) for r in rules))
        for c, rules in classes_of(user)
    ]
    default = [(name, color, False, sorted(rules)) for _, name, color, rules in DEFAULT_CLASSES]
    return found != default


def visible_classes(user) -> list[PersonClass]:
    """The classes of people the statistics show: without the hidden ones.

    Args:
        user: A user, or an anonymous one.

    Returns:
        The classes in their order.
    """
    return [c for c in class_list(user) if not c.hidden]


def class_list(user) -> list[PersonClass]:
    """The classes of people of a user (the defaults for visitors), in their order.

    Args:
        user: The user, or an anonymous one.

    Returns:
        The classes, also the hidden ones.
    """
    return [person_class for person_class, _ in classes_of(user)]


class Classifier:
    """Decides the class of an actor.

    The first class (in their order) with a rule that matches; None if there is none.
    """

    def __init__(
        self,
        user,
        locations: dict[str, str] | None = None,
        chosen: list[PersonClass] | None = None,
    ):
        """Decide the classes of the actors of a user's statistics.

        Args:
            user: The user, or an anonymous one, who gets the default classes.
            locations: The location of each login, for the rules of locations.
            chosen: Classes to use instead of those of the user, such as the ones of a
                shared address; None for the user's own.
        """
        if chosen is None:
            self.classes = classes_of(user)
        else:
            self.classes = [(c, list(c.rules.all())) for c in chosen]
        self.locations = locations or {}
        self.cache: dict[tuple, PersonClass | None] = {}

    def bot_class(self) -> PersonClass | None:
        """The first class with the rule "is a bot", None if there is none.

        Returns:
            The class.
        """
        return next(
            (c for c, rules in self.classes if any(r.kind == ClassRule.BOT for r in rules)), None
        )

    def __call__(self, login: str, association: str, is_bot: bool) -> PersonClass | None:
        """The class of an actor; remembered, as the same actors come again and again."""
        key = (login, association, is_bot)
        if key not in self.cache:
            location = self.locations.get(login, "")
            self.cache[key] = next(
                (
                    person_class
                    for person_class, rules in self.classes
                    if any(rule_matches(r, login, association, is_bot, location) for r in rules)
                ),
                None,
            )
        return self.cache[key]
