"""The superuser of DEFAULT_SUPERUSER: an email address, set each time the site starts."""

import pytest
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command

from community_insights.errors import InvalidDefaultSuperuser
from community_insights.management.commands.ensure_superuser import parse

pytestmark = pytest.mark.django_db
User = get_user_model()


def ensure(credentials=None):
    """Run ensure_superuser with the credentials, or with the environment."""
    call_command("ensure_superuser", *([credentials] if credentials else []))


def test_the_superuser_is_created_with_its_email_address():
    """The email address is the name; it is verified, so the superuser can sign in."""
    ensure("admin@example.com:a long password")
    user = User.objects.get()
    assert user.username == user.email == "admin@example.com"
    assert user.is_superuser and user.is_staff and user.is_active
    assert user.check_password("a long password")
    address = EmailAddress.objects.get(user=user)
    assert address.email == "admin@example.com" and address.verified and address.primary


def test_the_superuser_signs_in_with_the_email_address(client):
    """allauth signs in with the email address."""
    ensure("admin@example.com:a long password")
    response = client.post(
        "/accounts/login/", {"login": "admin@example.com", "password": "a long password"}
    )
    assert response.status_code == 302


def test_each_start_sets_the_password_and_the_rights_again():
    """A changed password in the setting is the new password; lost rights come back."""
    ensure("admin@example.com:first password")
    User.objects.update(is_superuser=False, is_staff=False, is_active=False)
    ensure("admin@example.com:second password")
    user = User.objects.get()
    assert user.check_password("second password") and not user.check_password("first password")
    assert user.is_superuser and user.is_staff and user.is_active
    assert EmailAddress.objects.count() == 1


def test_the_setting_is_read_from_the_environment(monkeypatch):
    """Without an argument, DEFAULT_SUPERUSER is used; without it nothing happens."""
    monkeypatch.delenv("DEFAULT_SUPERUSER", raising=False)
    ensure()
    assert not User.objects.exists()
    monkeypatch.setenv("DEFAULT_SUPERUSER", "  ")
    ensure()
    assert not User.objects.exists()
    monkeypatch.setenv("DEFAULT_SUPERUSER", "admin@example.com:from the environment")
    ensure()
    assert User.objects.get().check_password("from the environment")


def test_an_existing_account_of_the_address_becomes_the_superuser():
    """Somebody who signed up with the address is made superuser, not a second account."""
    person = User.objects.create_user("kim", "Admin@Example.com", "old password")
    EmailAddress.objects.create(user=person, email="other@example.com", primary=True)
    ensure("admin@example.com:a long password")
    person.refresh_from_db()
    assert User.objects.count() == 1 and person.is_superuser
    assert person.check_password("a long password")
    primary = EmailAddress.objects.get(user=person, primary=True)
    assert primary.email == "admin@example.com" and primary.verified


def test_the_address_is_in_lower_case_and_the_password_may_contain_colons():
    """Upper case letters of the address do not make another account."""
    ensure("Admin@Example.COM:pass:word")
    ensure("admin@example.com:pass:word")
    user = User.objects.get()
    assert user.email == "admin@example.com" and user.check_password("pass:word")


@pytest.mark.parametrize(
    ("credentials", "message"),
    [
        ("admin:admin", "is no email address"),
        ("admin@example.com", "the password is missing"),
        ("admin@example.com:", "the password is missing"),
        (":password", "is no email address"),
        ("not an address:password", "is no email address"),
    ],
)
def test_invalid_settings_say_what_to_write(credentials, message):
    """An old name:password or a missing password stops with what to write and a link."""
    with pytest.raises(InvalidDefaultSuperuser, match=message):
        parse(credentials)
    with pytest.raises(CommandError, match=message) as error:
        ensure(credentials)
    assert InvalidDefaultSuperuser.docs_url() in str(error.value)
    assert not User.objects.exists()


def test_the_production_check_refuses_the_name_of_the_address_as_password(settings):
    """admin@example.com with the password admin does not start in production."""
    ensure("admin@example.com:admin")
    settings.PRODUCTION = True
    with pytest.raises(CommandError, match="admin@example.com"):
        call_command("check_production")
    ensure("admin@example.com:admin@example.com")
    with pytest.raises(CommandError):
        call_command("check_production")
    ensure("admin@example.com:a long and good password")
    call_command("check_production")


def test_the_demo_project_goes_to_the_superuser_by_its_address():
    """demo_data finds the user by the email address, also by the name."""
    from community_insights.demo import DEMO

    ensure("admin@example.com:a long password")
    call_command("demo_data", "ADMIN@example.com")
    assert User.objects.get().projects.get().target == DEMO
    with pytest.raises(CommandError, match="nobody@example.com"):
        call_command("demo_data", "nobody@example.com")
