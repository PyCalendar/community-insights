"""manage.py prepare: the steps before the container serves, in one process."""

from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command

from community_insights.management.commands.prepare import STEPS

pytestmark = pytest.mark.django_db
ROOT = Path(__file__).parents[2]


def test_prepare_creates_the_superuser_and_checks_it(monkeypatch, settings):
    """The superuser of DEFAULT_SUPERUSER is made, and its good password passes."""
    settings.PRODUCTION = True
    monkeypatch.setenv("DEFAULT_SUPERUSER", "boss@example.org:a long and good password")
    call_command("prepare")
    assert get_user_model().objects.get(email="boss@example.org").is_superuser


def test_prepare_stops_at_a_default_password(monkeypatch, settings):
    """In production, a superuser with a default password stops the start."""
    settings.PRODUCTION = True
    monkeypatch.setenv("DEFAULT_SUPERUSER", "admin@example.org:admin")
    with pytest.raises(CommandError, match="default password"):
        call_command("prepare")


def test_prepare_runs_the_steps_in_order(monkeypatch):
    """Migrate first, the check of the passwords last."""
    called = []
    monkeypatch.setattr(
        "community_insights.management.commands.prepare.call_command",
        lambda name, **options: called.append(name),
    )
    call_command("prepare")
    assert called == [name for name, _ in STEPS]
    assert called[0] == "migrate"
    assert called[-1] == "check_production"


def test_the_container_prepares_in_one_process():
    """start-service.sh starts Django once before it serves, not once for each step."""
    script = (ROOT / "docker" / "start-service.sh").read_text()
    assert "manage.py prepare" in script
    for name, _ in STEPS:
        assert f"manage.py {name}" not in script


def test_the_health_check_waits_for_the_start():
    """Failed health checks while the container starts do not make it unhealthy."""
    dockerfile = (ROOT / "Dockerfile").read_text()
    assert "HEALTHCHECK --start-period=" in dockerfile
