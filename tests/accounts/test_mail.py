"""The mails of the accounts."""

import pytest
from django.core import mail

pytestmark = pytest.mark.django_db


PASSWORD = "a long password 123"


def sign_up(client, email="new@example.org"):
    """Sign up with an email address and the password of the tests."""
    return client.post(
        "/accounts/signup/",
        {"email": email, "password1": PASSWORD, "password2": PASSWORD},
    )


def test_sign_up_sends_a_confirmation(client):
    """Sign up sends a confirmation."""
    response = sign_up(client)
    assert response.status_code == 302
    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == ["new@example.org"]
    assert "/accounts/confirm-email/" in message.body


def test_optional_confirmation_lets_people_in(client):
    """Optional confirmation lets people in."""
    sign_up(client)
    assert client.get("/dashboard/").status_code == 200


def test_mandatory_confirmation(client, settings):
    """Mandatory confirmation."""
    settings.ACCOUNT_EMAIL_VERIFICATION = "mandatory"
    sign_up(client)
    assert client.get("/dashboard/").status_code == 302


def test_password_reset_mail(client):
    """Password reset mail."""
    sign_up(client)
    client.logout()
    mail.outbox.clear()
    client.post("/accounts/password/reset/", {"email": "new@example.org"})
    assert len(mail.outbox) == 1 and "/accounts/password/reset/key/" in mail.outbox[0].body


def test_mail_settings(settings):
    """Mail settings."""
    from django.conf import settings as live

    assert live.EMAIL_BACKEND.endswith(("console.EmailBackend", "locmem.EmailBackend"))
    assert live.EMAIL_PORT == 587 and live.EMAIL_USE_TLS
