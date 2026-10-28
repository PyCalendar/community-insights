"""The progress bar of the data, asked again by htmx while fetches run."""

import pytest

from community_insights import errors
from community_insights.models import FetchJob

pytestmark = pytest.mark.django_db

HTMX = {"HTTP_HX_REQUEST": "true", "HTTP_HX_CURRENT_URL": "http://testserver/s/1/contributors/"}


def test_the_page_asks_again_while_fetches_run(world, signed_in):
    """With running fetches, the bar has the attributes of htmx to ask every 4 seconds."""
    pk = world["project"].pk
    page = signed_in.get(f"/s/{pk}/").content.decode()
    assert f'hx-get="/s/{pk}/progress.json"' in page and 'hx-trigger="every 4s"' in page
    assert "vendor/htmx/htmx.min.js" in page and "js/progress.js" not in page


def test_htmx_gets_the_bar_with_the_fetches(world, signed_in):
    """htmx gets the part of the page, not JSON; its link goes back to the page shown."""
    pk = world["project"].pk
    response = signed_in.get(f"/s/{pk}/progress.json", **HTMX)
    page = response.content.decode()
    assert response["Content-Type"].startswith("text/html")
    assert page.lstrip().startswith('<div id="data-progress"')
    assert "o/r: running" in page and "o/r: queued" in page
    assert "next=/s/1/contributors/" in page


def test_the_page_is_loaded_again_when_the_fetches_ended(world, signed_in):
    """Without fetches, htmx is told to load the page again, with the new statistics."""
    FetchJob.objects.filter(status__in=["queued", "running"]).update(status="done")
    response = signed_in.get(f"/s/{world['project'].pk}/progress.json", **HTMX)
    assert response["HX-Refresh"] == "true"


def test_without_fetches_the_page_does_not_ask(world, signed_in):
    """A page without running fetches has no polling."""
    FetchJob.objects.filter(status__in=["queued", "running"]).update(status="done")
    page = signed_in.get(f"/s/{world['project'].pk}/").content.decode()
    assert 'id="data-progress"' in page and "hx-get" not in page


def test_an_error_is_shown_in_the_bar_and_asked_again_later(world, signed_in, monkeypatch):
    """An error shows its title, its text and what to do; htmx asks again, slower."""

    def broken(repositories):
        """Fail as if GitHub could not be reached."""
        raise errors.GitHubUnreachable("down")

    monkeypatch.setattr("community_insights.pipeline.completeness", broken)
    response = signed_in.get(f"/s/{world['project'].pk}/progress.json", **HTMX)
    page = response.content.decode()
    assert response.status_code == 200, "htmx swaps only answers that are OK"
    assert "GitHub cannot be reached: down" in page
    assert errors.GitHubUnreachable.docs_url() in page
    assert 'hx-trigger="every 8s"' in page


def test_htmx_asking_for_an_unknown_scope_is_not_found(world, signed_in):
    """A scope that does not exist is not found, also for htmx."""
    assert signed_in.get("/s/999999/progress.json", **HTMX).status_code == 404


def test_htmx_from_a_visitor_on_public_statistics(world, client):
    """Visitors see the progress of public repositories, too."""
    response = client.get("/s/o~r/progress.json", **HTMX)
    assert response.status_code == 200
    assert "o/r: running" in response.content.decode(), "the fetches of the repository"
