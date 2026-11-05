"""The page Users: the accounts of the site and who is an administrator."""

from allauth.socialaccount.models import SocialAccount
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from ..errors import CannotRemoveOwnAdminAccess
from ..feedback import show_error


def github_login(user) -> str:
    """The handle of the GitHub account linked to a user.

    Args:
        user: A user whose ``socialaccount_set`` holds only the GitHub accounts.

    Returns:
        The handle, "" if no GitHub account is linked.
    """
    for account in user.socialaccount_set.all():
        if login := (account.extra_data or {}).get("login"):
            return login
    return ""


def set_admin(acting, user, admin: bool) -> None:
    """Make a user an administrator (staff and superuser) or remove that access.

    Args:
        acting: The administrator who changes it.
        user: The user changed.
        admin: True to give the access, False to remove it.

    Raises:
        CannotRemoveOwnAdminAccess: If administrators remove their own access.
    """
    if not admin and user.pk == acting.pk:
        raise CannotRemoveOwnAdminAccess(
            _("Ask another administrator to remove your administrator access.")
        )
    user.is_staff = user.is_superuser = admin
    user.save(update_fields=["is_staff", "is_superuser"])


@login_required
def users(request):
    """The page Users: every account, its GitHub handle, and making it an administrator.

    Args:
        request: The request; a POST with ``user`` and ``admin`` ("1" or "0") changes the
            administrator access of that user.

    Returns:
        The page, or a redirect to it after a change.

    Raises:
        PermissionDenied: If the user is no administrator (superuser).
    """
    if not request.user.is_superuser:
        raise PermissionDenied(_("Only the administrators may see the users."))
    if request.method == "POST":
        user = get_object_or_404(get_user_model(), pk=request.POST.get("user"))
        admin = request.POST.get("admin") == "1"
        try:
            set_admin(request.user, user, admin)
        except Exception as error:  # shown with what to do
            show_error(request, error, _("Not changed. "))
        else:
            if admin:
                messages.success(request, _("%(name)s is an administrator.") % {"name": user})
            else:
                messages.success(
                    request, _("%(name)s is no administrator any more.") % {"name": user}
                )
        return redirect("users")
    accounts = (
        get_user_model()
        .objects.order_by("username")
        .prefetch_related(
            Prefetch("socialaccount_set", queryset=SocialAccount.objects.filter(provider="github"))
        )
    )
    return render(
        request,
        "community/users.html",
        {"accounts": [(user, github_login(user)) for user in accounts]},
    )
