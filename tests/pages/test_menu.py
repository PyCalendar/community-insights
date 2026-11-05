"""The menu of the site: signed in, the pages of the account are in one drop-down."""

import re

import pytest

from community_insights.models import Message

pytestmark = pytest.mark.django_db

ACCOUNT_LINKS = [
    "Dashboard",
    "Explore",
    "Messages",
    "Downloads",
    "---",
    "Profile",
    "GitHub access",
    "Classes",
    "---",
    "Sign out",
]


def menu(html: str) -> str:
    """The menu of a page.

    Args:
        html: The page.

    Returns:
        The HTML of the menu.
    """
    return html[html.index("<nav") : html.index("</nav>")]


def account_menu(html: str) -> list[str]:
    """The entries of the account menu, in order; a divider is ``---``.

    Args:
        html: The page.

    Returns:
        The texts of the entries.
    """
    part = html[html.index('class="dropdown account-menu"') :]
    part = part[: part.index("</ul>")]
    entries = re.findall(r'class="dropdown-(?:item|divider)"[^>]*>([^<]*)', part)
    return [entry.strip() or "---" for entry in entries]


def test_the_account_menu_has_the_pages_in_order(signed_in):
    """Dashboard, Explore, Messages, Downloads; Profile, GitHub access, Classes; Sign out."""
    assert account_menu(signed_in.get("/dashboard/").content.decode()) == ACCOUNT_LINKS


def test_sign_out_does_not_show_the_email(signed_in, user):
    """The button to sign out shows neither the email nor the name of the account."""
    html = menu(signed_in.get("/dashboard/").content.decode())
    assert user.email not in html
    assert "Sign out alice" not in html


def test_sign_out_is_a_post_to_the_logout(signed_in):
    """Signing out is a form that posts, as allauth needs."""
    html = menu(signed_in.get("/dashboard/").content.decode())
    assert re.search(r'<form method="post" action="/accounts/logout/">', html)


def test_explore_is_only_in_the_account_menu_when_signed_in(signed_in):
    """Signed in, Explore is below Dashboard and not a link of its own in the bar."""
    html = menu(signed_in.get("/dashboard/").content.decode())
    assert 'class="nav-link" href="/explore/"' not in html


def test_administrators_have_their_section_above_sign_out(client):
    """Staff superusers: Cache, Admin and Users between Classes and Sign out."""
    from django.contrib.auth import get_user_model

    client.force_login(get_user_model().objects.create_superuser("root", "r@example.org", "pw"))
    entries = account_menu(client.get("/dashboard/").content.decode())
    assert entries[entries.index("Classes") :] == [
        "Classes",
        "---",
        "Cache",
        "Admin",
        "Users",
        "---",
        "Sign out",
    ]


def test_staff_without_superuser_have_no_users(signed_in, user):
    """The page Users is for superusers; staff see Cache and Admin."""
    user.is_staff = True
    user.save()
    entries = account_menu(signed_in.get("/dashboard/").content.decode())
    assert "Cache" in entries and "Admin" in entries and "Users" not in entries


def test_others_have_no_administrator_section(signed_in):
    """Without staff, there is no Cache, Admin or Users."""
    entries = account_menu(signed_in.get("/dashboard/").content.decode())
    assert not {"Cache", "Admin", "Users"} & set(entries)


def test_visitors_see_explore_and_sign_in(client):
    """Visitors have Explore in the bar, Sign in and Sign up, and no account menu."""
    html = menu(client.get("/").content.decode())
    assert 'class="nav-link" href="/explore/"' in html
    assert "account-menu" not in html
    assert "Sign in" in html and "Sign up" in html


def test_the_unread_messages_are_counted_on_the_account_button(signed_in, user):
    """The number of unread messages is seen without opening the menu."""
    Message.objects.create(user=user, title="ready")
    html = signed_in.get("/dashboard/").content.decode()
    account = html[html.index('class="dropdown account-menu"') :]
    button = account[: account.index("</button>")]
    assert 'title="unread">1</span>' in button
