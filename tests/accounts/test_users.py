"""The page Users: administrators see the accounts and make others administrators."""

import pytest
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model

from community_insights.errors import CannotRemoveOwnAdminAccess
from community_insights.views.users import set_admin

pytestmark = pytest.mark.django_db


@pytest.fixture
def root(db):
    """A superuser.

    Returns:
        The user.
    """
    return get_user_model().objects.create_superuser("root", "root@example.org", "pw")


@pytest.fixture
def root_client(client, root):
    """A client signed in as the superuser.

    Returns:
        The client.
    """
    client.force_login(root)
    return client


def test_the_users_are_listed_with_their_github_handle(root_client, user):
    """Each account is a row; a linked GitHub account shows its handle, linked."""
    SocialAccount.objects.create(user=user, provider="github", uid="7", extra_data={"login": "al"})
    html = root_client.get("/dashboard/users/").content.decode()
    assert 'data-user="alice"' in html and 'data-user="root"' in html
    assert '<a href="https://github.com/al">al</a>' in html
    assert "alice@example.org" in html


def test_a_user_without_github_says_not_linked(root_client, user):
    """Without a linked account the column says so."""
    html = root_client.get("/dashboard/users/").content.decode()
    row = html[html.index('data-user="alice"') :]
    assert "not linked" in row[: row.index("</tr>")]


def test_a_github_account_from_another_provider_is_not_shown(root_client, user):
    """The page only shows handles of GitHub."""
    SocialAccount.objects.create(user=user, provider="gitlab", uid="1", extra_data={"login": "gl"})
    assert "gl</a>" not in root_client.get("/dashboard/users/").content.decode()


def test_make_a_user_admin_and_remove_it(root_client, user):
    """Making admin gives staff and superuser; removing takes both."""
    response = root_client.post("/dashboard/users/", {"user": user.pk, "admin": "1"}, follow=True)
    user.refresh_from_db()
    assert user.is_staff and user.is_superuser
    assert "alice is an administrator." in response.content.decode()
    response = root_client.post("/dashboard/users/", {"user": user.pk, "admin": "0"}, follow=True)
    user.refresh_from_db()
    assert not user.is_staff and not user.is_superuser
    assert "alice is no administrator any more." in response.content.decode()


def test_administrators_cannot_remove_their_own_access(root_client, root):
    """The own access stays, so the site keeps an administrator; the error says why."""
    response = root_client.post("/dashboard/users/", {"user": root.pk, "admin": "0"}, follow=True)
    root.refresh_from_db()
    assert root.is_superuser and root.is_staff
    html = response.content.decode()
    assert "Your own administrator access stays" in html
    assert CannotRemoveOwnAdminAccess.docs_url() in html


def test_set_admin_refuses_the_own_access(root):
    """The rule is in set_admin, not only in the page."""
    with pytest.raises(CannotRemoveOwnAdminAccess):
        set_admin(root, root, admin=False)


def test_the_own_row_has_no_remove_button(root_client):
    """There is no button that would only fail."""
    html = root_client.get("/dashboard/users/").content.decode()
    row = html[html.index('data-user="root"') :]
    assert "Remove admin" not in row[: row.index("</tr>")]


def test_an_unknown_user_is_not_found(root_client):
    """A user that does not exist gives 404."""
    assert root_client.post("/dashboard/users/", {"user": 999, "admin": "1"}).status_code == 404


def test_the_page_is_for_superusers_only(signed_in, user):
    """Others are not allowed, also staff who are no superusers."""
    assert signed_in.get("/dashboard/users/").status_code == 403
    assert signed_in.post("/dashboard/users/", {"user": user.pk, "admin": "1"}).status_code == 403
    user.refresh_from_db()
    assert not user.is_superuser
    user.is_staff = True
    user.save()
    assert signed_in.get("/dashboard/users/").status_code == 403


def test_visitors_are_sent_to_sign_in(client):
    """Visitors must sign in first."""
    response = client.get("/dashboard/users/")
    assert response.status_code == 302 and "/accounts/login/" in response["Location"]
