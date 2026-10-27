from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from ..classify import ensure_default_classes
from ..errors import UnknownRuleKind
from ..feedback import show_error
from ..models import (
    ClassRule,
    PersonClass,
)


@login_required
def classes(request):
    """The page Classes of people: add, order and delete classes and rules."""
    user = request.user
    ensure_default_classes(user)
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "add_class":
                PersonClass.objects.create(
                    user=user,
                    name=request.POST["name"].strip()[:60],
                    color=request.POST.get("color", "#649568"),
                )
            elif action == "delete_class":
                get_object_or_404(PersonClass, pk=request.POST["id"], user=user).delete()
            elif action == "add_rule":
                target = get_object_or_404(PersonClass, pk=request.POST["id"], user=user)
                kind = request.POST["kind"]
                if kind not in dict(ClassRule.KINDS):
                    raise UnknownRuleKind(f"There is no kind of rule {kind!r}.")
                target.rules.create(kind=kind, value=request.POST.get("value", "").strip())
            elif action == "delete_rule":
                get_object_or_404(
                    ClassRule, pk=request.POST["id"], person_class__user=user
                ).delete()
            elif action in ("up", "down"):
                moved = get_object_or_404(PersonClass, pk=request.POST["id"], user=user)
                moved.up() if action == "up" else moved.down()
        except Exception as error:  # shown with what to do
            show_error(request, error, _("Not saved. "))
        return redirect("classes")
    return render(
        request,
        "community/classes.html",
        {"classes": user.classes.prefetch_related("rules"), "kinds": ClassRule.KINDS},
    )
