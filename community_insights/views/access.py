from allauth.socialaccount.models import SocialAccount
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from ..errors import InvalidPercentage, LimitNotANumber, LimitTooSmall, MissingToken
from ..feedback import show_error
from ..models import (
    AccessToken,
    Profile,
    Repository,
)
from ..tokens import ask_one
from ..tokens.access import mirror_linked_account

EXPIRY_WARNING_DAYS = 14


def positive_or_none(text: str) -> int | None:
    """A whole number above 0 of a form, or None if empty; InvalidLimit otherwise."""
    text = (text or "").strip()
    if not text:
        return None
    try:
        value = int(text)
    except ValueError:
        raise LimitNotANumber(f"{text!r} is no whole number.") from None
    if value < 1:
        raise LimitTooSmall("The limit must be at least 1, or empty for no limit.")
    return value


def percent(text, default: int) -> int:
    """A percentage of a slider, 0 to 100."""
    text = (text or "").strip()
    if not text:
        return default
    try:
        value = int(text)
    except ValueError:
        raise InvalidPercentage(f"{text!r} is no whole number.") from None
    if not 0 <= value <= 100:
        raise InvalidPercentage("A percentage is between 0 and 100.")
    return value


def add_token(request, user):
    """Check a token with GitHub and store it with its sliders; warn if it never expires."""
    token = request.POST.get("token", "").strip()
    if not token:
        raise MissingToken("Please paste a token.")
    max_percent = percent(request.POST.get("max_percent"), 100)
    shared_percent = percent(request.POST.get("shared_percent"), 10)
    login, client = ask_one(token, "viewer")
    rate = client.rate
    stored = AccessToken.objects.create(
        user=user,
        token=token,
        login=login,
        label=request.POST.get("label", "").strip()[:100],
        max_percent=max_percent,
        shared_percent=shared_percent,
        expires_at=rate.expires_at,
        rate_limit=rate.limit,
        rate_remaining=rate.remaining,
        rate_reset_at=rate.reset_at,
    )
    messages.success(request, _("The token of %(login)s was saved.") % {"login": login})
    if rate.expires_at is None:
        messages.warning(
            request,
            _(
                "This token never expires, or GitHub did not tell. Some organisations, "
                "such as Plone, refuse tokens without an expiration date: their "
                "repositories cannot be read with it."
            ),
        )
    return stored


def test_token(stored: AccessToken) -> dict:
    """Can the token read every repository of the projects of its user?"""
    names = sorted(
        Repository.objects.filter(projects__user=stored.user)
        .distinct()
        .values_list("full_name", flat=True)
    )
    visible, client = ask_one(stored.token, "visible", names) if names else ({}, None)
    result = {
        "checked": timezone.now().isoformat(),
        "ok": sum(visible.values()),
        "total": len(names),
        "missing": [name for name, seen in visible.items() if not seen],
    }
    stored.last_test = result
    if client is not None:
        stored.expires_at = client.rate.expires_at or stored.expires_at
        stored.rate_remaining = client.rate.remaining
        stored.rate_reset_at = client.rate.reset_at
    stored.last_error = stored.last_error_code = ""
    stored.save()
    return result


@login_required
def github_access(request):
    """The page GitHub access: the linked account, the tokens and the profile."""
    user = request.user
    profile = Profile.of(user)
    if request.method == "POST":
        action = request.POST.get("action", "add")
        try:
            if action == "add":
                add_token(request, user)
            elif action == "delete":
                get_object_or_404(
                    AccessToken, pk=request.POST["id"], user=user, linked=False
                ).delete()
                messages.success(request, _("The token was deleted."))
            elif action in ("up", "down"):
                moved = get_object_or_404(AccessToken, pk=request.POST["id"], user=user)
                moved.up() if action == "up" else moved.down()
            elif action == "share":
                stored = get_object_or_404(AccessToken, pk=request.POST["id"], user=user)
                stored.max_percent = percent(request.POST.get("max_percent"), stored.max_percent)
                stored.shared_percent = percent(
                    request.POST.get("shared_percent"), stored.shared_percent
                )
                stored.save()
                messages.success(
                    request,
                    _("%(token)s: up to %(max)s points per hour, %(shared)s of them for others.")
                    % {"token": stored, "max": stored.max_points, "shared": stored.shared_points},
                )
            elif action == "test":
                stored = get_object_or_404(AccessToken, pk=request.POST["id"], user=user)
                result = test_token(stored)
                if result["missing"]:
                    messages.warning(
                        request,
                        _("%(token)s cannot read %(missing)s of %(total)s repositories: %(names)s")
                        % {
                            "token": stored,
                            "missing": len(result["missing"]),
                            "total": result["total"],
                            "names": ", ".join(result["missing"]),
                        },
                    )
                else:
                    messages.success(
                        request,
                        _("%(token)s can read all %(total)s repositories.")
                        % {"token": stored, "total": result["total"]},
                    )
            elif action == "profile":
                profile.fetch_limit = positive_or_none(request.POST.get("fetch_limit")) or 5000
                profile.show_horizon_europe = request.POST.get("show_horizon_europe") == "on"
                profile.save()
                messages.success(request, _("Saved."))
        except Exception as error:  # shown with what to do
            show_error(request, error, _("Not saved. "))
        return redirect("github_access")
    now = timezone.now()
    mirror_linked_account(user)
    tokens = list(user.access_tokens.all())
    for token in tokens:
        token.expires_soon = bool(
            token.expires_at and (token.expires_at - now).days < EXPIRY_WARNING_DAYS
        )
        token.expired = bool(token.expires_at and token.expires_at <= now)
    return render(
        request,
        "community/github_access.html",
        {
            "account": SocialAccount.objects.filter(user=user, provider="github").first(),
            "tokens": tokens,
            "profile": profile,
        },
    )
