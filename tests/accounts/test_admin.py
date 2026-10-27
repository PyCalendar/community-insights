"""The Django admin: every table, for superusers only."""

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model

pytestmark = pytest.mark.django_db


MODELS = list(apps.get_app_config("community").get_models())


@pytest.fixture
def admin_client(client):
    superuser = get_user_model().objects.create_superuser("root", "root@example.org", "pw")
    client.force_login(superuser)
    return client


def test_the_menu_of_a_superuser_has_the_admin(admin_client):
    page = admin_client.get("/dashboard/").content.decode()
    assert 'href="/admin/"' in page


def test_others_have_no_admin_in_the_menu(user, client):  # noqa: F811
    client.force_login(user)
    assert 'href="/admin/"' not in client.get("/dashboard/").content.decode()
    assert client.get("/admin/").status_code == 302


@pytest.mark.parametrize("model", MODELS, ids=lambda m: m.__name__)
def test_every_table_can_be_browsed(world, admin_client, model):  # noqa: F811
    meta = model._meta
    listing = admin_client.get(f"/admin/{meta.app_label}/{meta.model_name}/?q=a")
    assert listing.status_code == 200, meta.model_name
    first = model.objects.first()
    if first is not None:
        page = admin_client.get(f"/admin/{meta.app_label}/{meta.model_name}/{first.pk}/change/")
        assert page.status_code == 200


def test_secrets_are_not_shown(world, admin_client):  # noqa: F811
    from community_insights.models import AccessToken, Project

    token = AccessToken.objects.first()
    page = admin_client.get(f"/admin/community/accesstoken/{token.pk}/change/").content.decode()
    assert 'name="token"' not in page
    project = Project.objects.first()
    listing = admin_client.get("/admin/community/project/").content.decode()
    assert project.badge_token not in listing


def test_the_admin_is_signed_in_to_like_the_site(client, db):
    response = client.get("/admin/login/?next=/admin/")
    assert response.status_code == 302 and response["Location"].startswith("/accounts/login/")
