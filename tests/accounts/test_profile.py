"""The profile: email addresses, password, the linked GitHub account and the tokens."""

import pytest
from allauth.account.models import EmailAddress
from django.core import mail

from community_insights.models import AccessToken

pytestmark = pytest.mark.django_db


def test_the_profile_needs_an_account(client):
    """Visitors are sent to sign in."""
    response = client.get("/dashboard/profile/")
    assert response.status_code == 302 and "/accounts/login/" in response["Location"]


def test_the_menu_links_the_profile(signed_in):
    """Signed in, the menu has Profile."""
    assert 'href="/dashboard/profile/"' in signed_in.get("/dashboard/").content.decode()


def test_the_profile_shows_the_email_addresses_and_their_state(user, signed_in):
    """Confirmed and not confirmed addresses, the primary one first."""
    EmailAddress.objects.create(user=user, email="alice@example.org", primary=True, verified=True)
    EmailAddress.objects.create(user=user, email="work@example.org", verified=False)
    page = signed_in.get("/dashboard/profile/").content.decode()
    assert page.index('data-email="alice@example.org"') < page.index(
        'data-email="work@example.org"'
    )
    confirmed = page[page.index('data-email="alice@example.org"') :]
    assert "confirmed" in confirmed[: confirmed.index("</li>")]
    unconfirmed = page[page.index('data-email="work@example.org"') :]
    assert "Send the confirmation again" in unconfirmed[: unconfirmed.index("</li>")]
    assert 'href="/accounts/email/"' in page


def test_the_confirmation_is_sent_again(user, signed_in):
    """The button sends the confirmation of the address with django-allauth."""
    EmailAddress.objects.create(user=user, email="work@example.org", verified=False)
    response = signed_in.post(
        "/accounts/email/", {"email": "work@example.org", "action_send": ""}, follow=True
    )
    assert response.status_code == 200
    assert [m.to for m in mail.outbox] == [["work@example.org"]]


def test_the_password_can_be_changed_set_and_reset(user, signed_in):
    """With a password: change it; without one (GitHub only): set it; always: reset it."""
    page = signed_in.get("/dashboard/profile/").content.decode()
    assert 'href="/accounts/password/change/"' in page
    assert 'href="/accounts/password/reset/"' in page
    user.set_unusable_password()
    user.save()
    signed_in.force_login(user)
    page = signed_in.get("/dashboard/profile/").content.decode()
    assert 'href="/accounts/password/set/"' in page
    assert 'href="/accounts/password/change/"' not in page


def test_the_linked_github_account_is_shown(signed_in):
    """The login of the linked account, with the page to manage the links."""
    page = signed_in.get("/dashboard/profile/").content.decode()
    assert "Linked with the GitHub account <strong>alice</strong>" in page
    assert 'href="/accounts/3rdparty/"' in page


def test_without_a_linked_account_it_offers_to_link_one(user, signed_in):
    """Without a link, the button links one, as on GitHub access."""
    from allauth.socialaccount.models import SocialAccount

    SocialAccount.objects.filter(user=user).delete()
    page = signed_in.get("/dashboard/profile/").content.decode()
    assert "No GitHub account is linked." in page
    assert "/accounts/github/login/?process=connect" in page


def test_without_an_oauth_app_it_says_so(user, client):
    """An installation without the OAuth app of GitHub only offers tokens."""
    client.force_login(user)
    page = client.get("/dashboard/profile/").content.decode()
    assert "This installation has no GitHub OAuth app" in page


def test_the_tokens_are_listed_with_their_expiry(user, signed_in):
    """Expired and soon expiring tokens are marked; they are managed on GitHub access."""
    from datetime import timedelta

    from django.utils import timezone

    now = timezone.now()
    AccessToken.objects.create(user=user, token="a", login="a", label="old", expires_at=now)
    AccessToken.objects.create(
        user=user, token="b", login="b", label="soon", expires_at=now + timedelta(days=3)
    )
    AccessToken.objects.create(
        user=user, token="c", login="c", label="fine", expires_at=now + timedelta(days=90)
    )
    page = signed_in.get("/dashboard/profile/").content.decode()
    tokens = page[page.index('id="tokens"') :]
    assert tokens.count("expired") == 1 and tokens.count("expires soon") == 1
    assert 'href="/dashboard/github/"' in tokens


def test_without_tokens_it_says_so(user, client):
    """No token yet."""
    client.force_login(user)
    assert "No token yet." in client.get("/dashboard/profile/").content.decode()
