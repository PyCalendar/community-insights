"""Errors are shown with what to do."""

from community_insights import errors


def test_errors_are_shown_with_a_link_to_the_docs(world, signed_in, monkeypatch):  # noqa: F811
    """Errors are shown with a link to the docs."""
    response = signed_in.post("/dashboard/", {"target": "not a/valid/target"}, follow=True)
    page = response.content.decode()
    assert "Not a repository or organisation" in page
    assert errors.InvalidTarget.docs_url() in page and "What to do" in page


def test_unexpected_errors_are_shown_too(world, signed_in, monkeypatch):  # noqa: F811
    """Unexpected errors are shown too."""

    def boom(*args, **kwargs):
        """Fail with an error the site does not know."""
        raise KeyError("surprise")

    monkeypatch.setattr("community_insights.views.dashboard.add_project", boom)
    page = signed_in.post("/dashboard/", {"target": "o/x"}, follow=True).content.decode()
    assert "Unexpected error" in page and "KeyError" in page


def test_failed_jobs_link_to_their_error(world, signed_in):  # noqa: F811
    """Failed jobs link to their error."""
    from community_insights.models import FetchJob

    FetchJob.objects.filter(status="failed").update(
        message="GitHub rejected the token.", error_code="InvalidAPIToken"
    )
    page = signed_in.get("/dashboard/downloads/").content.decode()
    assert errors.InvalidAPIToken.docs_url() in page


def test_progress_errors_are_json_with_what_to_do(world, signed_in, monkeypatch):  # noqa: F811
    """Progress errors are json with what to do."""
    import json

    def broken(repositories):
        """Fail as if GitHub could not be reached."""
        raise errors.GitHubUnreachable("down")

    monkeypatch.setattr("community_insights.pipeline.completeness", broken)
    response = signed_in.get(f"/s/{world['project'].pk}/progress.json")
    assert response.status_code == 500
    error = json.loads(response.content)["error"]
    assert error["title"] == "GitHub cannot be reached" and error["detail"] == "down"
    assert error["docs_url"] == errors.GitHubUnreachable.docs_url()


def test_query_errors_link_to_how_to_write_a_query(world, signed_in):  # noqa: F811
    """Query errors link to how to write a query."""
    pk = world["project"].pk
    page = signed_in.get(f"/s/{pk}/contributors/?where=nonsense_variable").content.decode()
    assert "There is no variable" in page
    assert "#community_insights.errors.input.UnknownVariable" in page, "what to do"
    assert 'href="https://community-insights.readthedocs.io/en/latest/how-to/queries.html"' in page
    assert "How to write a query" in page
    other = signed_in.get(f"/s/{pk}/?since=nonsense").content.decode()
    assert "Invalid time range" in other or "InvalidDate" in other
    alert = other[other.index('role="alert"') :]
    assert "how-to/queries.html#time-range" in alert, "the guide of the time range"
    assert 'how-to/queries.html"' not in alert and "How to write a query" not in alert
