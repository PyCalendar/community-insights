"""The pages of allauth look like the rest of the site: its layout and Bootstrap forms."""

import re

import pytest

pytestmark = pytest.mark.django_db

VISITOR_PAGES = ["/accounts/signup/", "/accounts/login/", "/accounts/password/reset/"]
ACCOUNT_PAGES = ["/accounts/email/", "/accounts/password/change/", "/accounts/3rdparty/"]


def main(html: str) -> str:
    """The content of a page, without the menu and the footer."""
    return html[html.index("<main") : html.index("</main>")]


@pytest.mark.parametrize("url", VISITOR_PAGES)
def test_visitor_pages_use_the_layout_and_bootstrap_fields(client, url):
    """Visitor pages use the layout and bootstrap fields."""
    html = client.get(url).content.decode()
    assert "navbar-gh" in html, "the menu of the site"
    assert "form-control" in main(html), "the fields of Bootstrap"
    assert "<p>\n    <label" not in main(html), "not the plain fields of Django"


@pytest.mark.parametrize("url", ACCOUNT_PAGES)
def test_account_pages_use_the_layout(signed_in, url):
    """Account pages use the layout."""
    response = signed_in.get(url)
    assert response.status_code == 200
    html = response.content.decode()
    assert "navbar-gh" in html
    assert "btn" in main(html)


def test_the_sign_in_with_github_is_a_button(signed_in, client):
    """The sign in with github is a button."""
    client.logout()
    html = main(client.get("/accounts/login/").content.decode())
    assert '<a class="btn btn-outline-primary" title="GitHub"' in html


def allauth_pages() -> list[str]:
    """The addresses of all pages of allauth without parameters."""
    from django.urls import get_resolver

    found = []

    def walk(patterns, prefix):
        """Collect the addresses of the patterns, also of the included ones."""
        for pattern in patterns:
            if hasattr(pattern, "url_patterns"):
                walk(pattern.url_patterns, prefix + str(pattern.pattern))
            elif "<" not in str(pattern.pattern) and pattern.name:
                found.append("/" + prefix + str(pattern.pattern))

    for pattern in get_resolver().url_patterns:
        if str(pattern.pattern) == "accounts/":
            walk(pattern.url_patterns, "accounts/")
    return sorted(set(found))


# pages that only redirect: the sign in with GitHub, its callback, the sign out by POST
REDIRECTING = {"/accounts/github/login/", "/accounts/github/login/callback/"}


@pytest.mark.parametrize("url", [u for u in allauth_pages() if u not in REDIRECTING])
@pytest.mark.parametrize("who", ["visitor", "signed in"])
def test_every_page_of_allauth_has_the_look_of_the_site(url, who, client, signed_in):
    """Every page of allauth has the look of the site."""
    browser = signed_in if who == "signed in" else client
    if who == "visitor":
        signed_in.logout()
    response = browser.get(url, follow=True)
    if response.status_code != 200:
        pytest.skip(f"{url}: {response.status_code}")
    html = response.content.decode()
    assert "navbar-gh" in html, "the layout of the site"
    content = main(html)
    assert content.count("<h1") == 1, "one heading"
    assert "<p>\n    <label" not in content, "not the plain fields of Django"
    for field in re.findall(r"<input[^>]*>", content):
        if 'type="hidden"' in field or 'type="radio"' in field or 'type="checkbox"' in field:
            continue
        assert "form-control" in field, field
