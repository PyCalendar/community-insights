import re

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext
from django.utils.translation import gettext as _

from .. import stats
from ..classify import Classifier, add_handle, bot_class, ensure_default_classes
from ..errors import (
    ClassNameTaken,
    InvalidClassOrder,
    InvalidColor,
    InvalidHandle,
    NoBotClass,
    PresetClassNotDeleted,
    UnknownRuleKind,
)
from ..feedback import show_error
from ..models import (
    ClassRule,
    PersonClass,
    Repository,
)
from ..stats.bot_suggestions import AT_LEAST, FAST

COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
HANDLE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})(?:\[bot\])?$")


def add_bot(user, login: str) -> ClassRule:
    """Add an account to the class for bots of a user, as a handle.

    Args:
        user: The user.
        login: The handle of the account.

    Returns:
        The rule with the handle.

    Raises:
        InvalidHandle: If the login is no GitHub handle.
        NoBotClass: If no class has the rule "is a bot".
    """
    if not HANDLE.match(login):
        raise InvalidHandle(gettext("%(login)s is no GitHub handle.") % {"login": repr(login)})
    target = bot_class(user)
    if target is None:
        raise NoBotClass('No class has the rule "is a bot".')
    return add_handle(target, login)


def add_class(user, name: str, color: str) -> PersonClass:
    """Create a class of people of a user, last in the order.

    Args:
        user: The user.
        name: The name, at most 60 characters are kept.
        color: The colour, such as ``#649568``.

    Returns:
        The class.

    Raises:
        ClassNameTaken: If the user has a class of that name.
        InvalidColor: If the colour is not like ``#649568``.
    """
    name = name.strip()[:60]
    if user.classes.filter(name=name).exists():
        raise ClassNameTaken(gettext("You have a class %(name)s already.") % {"name": repr(name)})
    if not COLOR.match(color):
        raise InvalidColor(gettext("%(color)s is no colour like #649568.") % {"color": repr(color)})
    return PersonClass.objects.create(user=user, name=name, color=color.lower())


def delete_class(user, pk) -> None:
    """Delete a class of people of a user; those the site made are only hidden.

    Args:
        user: The user.
        pk: The id of the class.

    Raises:
        Http404: If the user has no class with the id.
        PresetClassNotDeleted: If the site made the class.
    """
    person_class = get_object_or_404(PersonClass, pk=pk, user=user)
    if person_class.preset:
        raise PresetClassNotDeleted(
            gettext("%(name)s is a class of the site: hide it instead.")
            % {"name": person_class.name}
        )
    person_class.delete()


def add_rule(user, pk, kind: str, value: str) -> ClassRule:
    """Add a rule to a class of people of a user.

    Args:
        user: The user.
        pk: The id of the class.
        kind: The kind of the rule, one of ``ClassRule.KINDS``.
        value: The value, such as handles separated by spaces.

    Returns:
        The rule.

    Raises:
        Http404: If the user has no class with the id.
        UnknownRuleKind: If there is no kind of rule of that name.
    """
    target = get_object_or_404(PersonClass, pk=pk, user=user)
    if kind not in dict(ClassRule.KINDS):
        raise UnknownRuleKind(gettext("There is no kind of rule %(kind)s.") % {"kind": repr(kind)})
    return target.rules.create(kind=kind, value=value.strip())


def edit_class(user, pk, name: str, color: str) -> PersonClass:
    """Change the name and the colour of a class of a user.

    Args:
        user: The user.
        pk: The id of the class.
        name: The new name; empty keeps the old one.
        color: The new colour, such as ``#649568``.

    Returns:
        The class, saved.

    Raises:
        InvalidColor: If the colour is not like ``#649568``.
        ClassNameTaken: If another class of the user has the name.
    """
    person_class = get_object_or_404(PersonClass, pk=pk, user=user)
    if not COLOR.match(color):
        raise InvalidColor(gettext("%(color)s is no colour like #649568.") % {"color": repr(color)})
    person_class.name = name.strip()[:60] or person_class.name
    person_class.color = color.lower()
    try:
        with transaction.atomic():
            person_class.save()
    except IntegrityError:
        raise ClassNameTaken(
            gettext("You have a class %(name)s already.") % {"name": repr(person_class.name)}
        ) from None
    return person_class


def order_classes(user, ids: list[str]) -> None:
    """Put the classes of a user in this order, the first on top.

    Args:
        user: The user.
        ids: The ids of all classes of the user, the first on top.

    Raises:
        InvalidClassOrder: If the ids are not each class of the user once.
    """
    classes = {str(c.pk): c for c in user.classes.all()}
    if sorted(ids) != sorted(classes):
        raise InvalidClassOrder(gettext("The order does not name each of your classes once."))
    for position, pk in enumerate(ids):
        classes[pk].to(position)


def suggested_bots(user) -> list:
    """Accounts that answer like bots and are not in the class for bots yet.

    Args:
        user: The user, whose projects are looked at.

    Returns:
        The suggestions.
    """
    target = bot_class(user)
    classify = Classifier(user)
    repositories = Repository.objects.filter(projects__user=user).distinct()
    return [
        s
        for s in stats.bot_suggestions(repositories)
        if target is None or classify(s.login, "", False) != target
    ]


@login_required
def classes(request):
    """The page Classes of people: add, order and delete classes and rules.

    Args:
        request: The request; a POST changes the classes, as its ``action`` says.

    Returns:
        The page, or a redirect to it after a change.
    """
    user = request.user
    ensure_default_classes(user)
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "add_class":
                add_class(user, request.POST["name"], request.POST.get("color", "#649568"))
            elif action == "delete_class":
                delete_class(user, request.POST["id"])
            elif action in ("hide", "show"):
                hidden = get_object_or_404(PersonClass, pk=request.POST["id"], user=user)
                hidden.hidden = action == "hide"
                hidden.save(update_fields=["hidden"])
            elif action == "add_rule":
                add_rule(
                    user, request.POST["id"], request.POST["kind"], request.POST.get("value", "")
                )
            elif action == "delete_rule":
                get_object_or_404(
                    ClassRule, pk=request.POST["id"], person_class__user=user
                ).delete()
            elif action == "edit_class":
                edit_class(
                    user,
                    request.POST.get("id"),
                    request.POST.get("name", ""),
                    request.POST.get("color", ""),
                )
            elif action == "order":
                order_classes(user, request.POST.getlist("order"))
            elif action == "add_bot":
                add_bot(user, request.POST.get("login", "").strip())
            elif action in ("up", "down"):
                moved = get_object_or_404(PersonClass, pk=request.POST["id"], user=user)
                moved.up() if action == "up" else moved.down()
        except Exception as error:  # shown with what to do
            show_error(request, error, _("Not saved. "))
        return redirect("classes")
    return render(
        request,
        "community/classes.html",
        {
            "classes": user.classes.prefetch_related("rules"),
            "kinds": ClassRule.KINDS,
            "suggested_bots": suggested_bots(user),
            "bot_class": bot_class(user),
            "fast_minutes": FAST // 60,
            "at_least": AT_LEAST,
        },
    )
