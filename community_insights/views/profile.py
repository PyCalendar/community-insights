from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from .access import EXPIRY_WARNING_DAYS


@login_required
def profile(request):
    """The profile of the account: email addresses, password, the linked GitHub and tokens.

    The changes are made on the pages of django-allauth (email addresses, password, linked
    accounts) and on the page GitHub access (tokens); this page shows where things stand and
    links there.

    Args:
        request: The request.

    Returns:
        The page.
    """
    user = request.user
    now = timezone.now()
    tokens = list(user.access_tokens.all())
    for token in tokens:
        token.expired = bool(token.expires_at and token.expires_at <= now)
        token.expires_soon = bool(
            token.expires_at
            and not token.expired
            and (token.expires_at - now).days < EXPIRY_WARNING_DAYS
        )
    return render(
        request,
        "community/profile.html",
        {
            "addresses": EmailAddress.objects.filter(user=user).order_by("-primary", "email"),
            "github": SocialAccount.objects.filter(user=user, provider="github").first(),
            "tokens": tokens,
            "has_password": user.has_usable_password(),
        },
    )
