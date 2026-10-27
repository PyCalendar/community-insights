"""Classes of people for response times."""

from fnmatch import fnmatchcase

from .models import ClassRule, PersonClass

MEMBERS = ("owner", "member", "collaborator")
# in the palette of the website, told apart by lightness
DEFAULT_CLASSES = [
    ("bot", "#9ccc9c", [(ClassRule.BOT, "")]),
    ("collaborator or higher", "#2b5329", [(ClassRule.ASSOCIATION, " ".join(MEMBERS))]),
    ("external", "#149414", [(ClassRule.ANY, "")]),
]


def ensure_default_classes(user) -> None:
    """Give a user the default classes (bot, collaborator or higher, external) if they have none."""
    if user.classes.exists():
        return
    for name, color, rules in DEFAULT_CLASSES:
        person_class = PersonClass.objects.create(user=user, name=name, color=color)
        for kind, value in rules:
            person_class.rules.create(kind=kind, value=value)


def rule_matches(
    rule: ClassRule, login: str, association: str, is_bot: bool, location: str
) -> bool:
    """Whether a rule matches an actor: by handle, pattern, status, bot or location, in any case."""
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
                PersonClass(name=name, color=color),
                [ClassRule(kind=kind, value=value) for kind, value in rules],
            )
            for name, color, rules in DEFAULT_CLASSES
        ]
    ensure_default_classes(user)
    found = PersonClass.objects.filter(user=user).prefetch_related("rules")
    return [(person_class, list(person_class.rules.all())) for person_class in found]


def class_list(user) -> list[PersonClass]:
    """The classes of people of a user (the defaults for visitors), in their order."""
    return [person_class for person_class, _ in classes_of(user)]


class Classifier:
    """Decides the class of an actor.

    The first class (in their order) with a rule that matches; None if there is none.
    """

    def __init__(self, user, locations: dict[str, str] | None = None):
        self.classes = classes_of(user)
        self.locations = locations or {}
        self.cache: dict[tuple, PersonClass | None] = {}

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
