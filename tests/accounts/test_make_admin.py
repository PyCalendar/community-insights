"""manage.py make_admin and manage.py name_site, run at the command line of the server."""

import pytest
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.management import CommandError, call_command

pytestmark = pytest.mark.django_db


def account(email: str, verified: bool):
    """An account with an email address, confirmed or not.

    Args:
        email: The address.
        verified: Whether it is confirmed.

    Returns:
        The user.
    """
    user = get_user_model().objects.create_user(email, email, "a long password")
    EmailAddress.objects.create(user=user, email=email, verified=verified, primary=True)
    return user


def test_a_confirmed_address_becomes_an_administrator():
    """The account with the confirmed address is staff and superuser, in any case."""
    user = account("kim@example.org", verified=True)
    call_command("make_admin", "Kim@Example.org")
    user.refresh_from_db()
    assert user.is_staff and user.is_superuser


def test_an_address_that_is_not_confirmed_stays():
    """Nobody becomes an administrator with an address that may not be theirs."""
    user = account("kim@example.org", verified=False)
    with pytest.raises(CommandError, match="Email address not confirmed"):
        call_command("make_admin", "kim@example.org")
    user.refresh_from_db()
    assert not user.is_superuser


def test_an_unknown_address():
    """No account with the address: the command says so."""
    with pytest.raises(CommandError, match="No account with this email address"):
        call_command("make_admin", "nobody@example.org")


def test_the_site_is_named_from_site_name(settings):
    """SITE_NAME names the first site at the start; without it, the name stays."""
    settings.SITE_NAME = "Insights of PyCalendar"
    call_command("name_site")
    assert Site.objects.get(pk=settings.SITE_ID).name == "Insights of PyCalendar"
    settings.SITE_NAME = ""
    call_command("name_site")
    assert Site.objects.get(pk=settings.SITE_ID).name == "Insights of PyCalendar"


def test_the_start_names_the_site(settings, monkeypatch):
    """manage.py prepare runs name_site."""
    from community_insights.management.commands.prepare import STEPS

    assert "name_site" in [name for name, _ in STEPS]
