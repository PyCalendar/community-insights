"""The pages in the language of the browser or the one chosen in the footer."""

import pytest
from django.utils import translation

from community_insights.errors import InvalidQuery

pytestmark = pytest.mark.django_db


def test_english_by_default(client):
    """English by default."""
    page = client.get("/explore/").content.decode()
    assert '<html lang="en"' in page
    assert ">Explore<" in page


def test_german_from_the_browser(client):
    """German from the browser."""
    page = client.get("/explore/", headers={"accept-language": "de-DE,de;q=0.9"}).content.decode()
    assert '<html lang="de"' in page
    assert ">Entdecken<" in page
    assert "Repositories durchsuchen" in page


def test_unknown_languages_are_english(client):
    """Unknown languages are english."""
    page = client.get("/explore/", headers={"accept-language": "tlh"}).content.decode()
    assert '<html lang="en"' in page


def test_the_switch_in_the_footer(client):
    """The switch in the footer."""
    page = client.get("/explore/").content.decode()
    assert 'name="language" data-submit-on-change' in page
    assert '<option value="de" lang="de">Deutsch</option>' in page
    assert ">English<" in page
    response = client.post("/i18n/setlang/", {"language": "de", "next": "/about/"})
    assert response.status_code == 302
    assert response["Location"] == "/about/"
    assert ">Über Contributor Community Insights<" in client.get("/about/").content.decode()


def test_the_switch_does_not_lead_away(client):
    """The switch does not lead away."""
    response = client.post("/i18n/setlang/", {"language": "de", "next": "https://evil.example"})
    assert response["Location"] == "/"


def test_signed_in_pages_in_german(world, signed_in):
    """Signed in pages in german."""
    signed_in.post("/i18n/setlang/", {"language": "de"})
    for url, text in [
        ("/dashboard/", "Offene Issues"),
        ("/dashboard/github/", "Höchstens genutzte Punkte pro Stunde"),
        (f"/s/{world['project'].pk}/", "Antwortzeiten"),
        (f"/s/{world['project'].pk}/contributors/", "Abfrage ausführen"),
        ("/dashboard/downloads/", "Beendet"),
        ("/dashboard/classes/", "Gruppen von Menschen"),
    ]:
        assert text in signed_in.get(url).content.decode(), url


def test_messages_in_german(world, signed_in):
    """Messages in german."""
    signed_in.post("/i18n/setlang/", {"language": "de"})
    response = signed_in.post(
        "/dashboard/github/", {"action": "profile", "fetch_limit": "800"}, follow=True
    )
    assert "Gespeichert." in response.content.decode()


def test_error_titles_are_translated():
    """Error titles are translated."""
    with translation.override("de"):
        assert str(InvalidQuery.title) == "Ungültige Abfrage"
        assert str(InvalidQuery()) == "Ungültige Abfrage"
    assert str(InvalidQuery.title) == "Invalid query"


def test_the_javascript_catalog(client):
    """The javascript catalog."""
    client.post("/i18n/setlang/", {"language": "de"})
    script = client.get("/jsi18n/").content.decode()
    assert "Eine Spalte hinzuf" in script  # ü is escaped in the script
    assert "function gettext" in script or "gettext" in script


def test_the_pages_load_the_javascript_catalog(client):
    """The pages load the javascript catalog."""
    assert 'src="/jsi18n/"' in client.get("/explore/").content.decode()


def test_the_languages_are_named_in_their_own_language(client):
    """The languages are named in their own language."""
    client.post("/i18n/setlang/", {"language": "de"})
    page = client.get("/explore/").content.decode()
    assert ">English<" in page
    assert ">Englisch<" not in page
    assert '<option value="de" lang="de" selected>Deutsch</option>' in page


def test_the_pages_in_spanish(client):
    """A browser that asks for Spanish gets the pages in Spanish, and can choose it."""
    page = client.get("/explore/", headers={"accept-language": "es"}).content.decode()
    assert '<html lang="es"' in page
    assert ">Explorar<" in page
    assert '<option value="es" lang="es" selected>español</option>' in page
