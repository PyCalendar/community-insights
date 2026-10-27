"""A production site does not start with default passwords."""

import pytest
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db


def test_production_refuses_default_passwords(db, settings):
    """Production refuses default passwords."""
    from django.core.management import CommandError, call_command

    get_user_model().objects.create_superuser("admin", "a@example.org", "admin")
    settings.PRODUCTION = False
    call_command("check_production")  # a local test site
    settings.PRODUCTION = True
    with pytest.raises(CommandError, match="default password"):
        call_command("check_production")
    admin = get_user_model().objects.get(username="admin")
    admin.set_password("a long and good password")
    admin.save()
    call_command("check_production")


def test_the_name_as_password_is_refused_too(db, settings):
    """The name as password is refused too."""
    from django.core.management import CommandError, call_command

    settings.PRODUCTION = True
    get_user_model().objects.create_superuser("kim", "k@example.org", "kim")
    with pytest.raises(CommandError, match="kim"):
        call_command("check_production")
