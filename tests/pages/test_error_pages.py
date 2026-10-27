"""The pages of errors have the look of the site."""

import pytest
from django.template.loader import render_to_string

pytestmark = pytest.mark.django_db


def test_a_missing_page_has_the_layout(client):
    """A missing page has the layout."""
    response = client.get("/s/nobody~nothing/")
    assert response.status_code == 404
    html = response.content.decode()
    assert "navbar-gh" in html and "<h1" in html and "Not found" in html


def test_a_page_that_is_not_allowed_has_the_layout(signed_in):
    """A page that is not allowed has the layout."""
    response = signed_in.get("/dashboard/cache/")
    assert response.status_code == 403
    html = response.content.decode()
    assert "navbar-gh" in html and "Not allowed" in html


def test_the_server_error_page_needs_no_request():
    """The server error page needs no request."""
    html = render_to_string("500.html")
    assert "navbar-gh" in html and "<h1" in html and "/static/style.css" in html
