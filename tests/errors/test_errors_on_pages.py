"""Errors are shown with what to do."""

from community_insights import errors


def test_errors_are_shown_with_a_link_to_the_docs(world, signed_in, monkeypatch):  # noqa: F811
    response = signed_in.post("/dashboard/", {"target": "not a/valid/target"}, follow=True)
    page = response.content.decode()
    assert "Not a repository or organisation" in page
    assert errors.InvalidTarget.docs_url() in page and "What to do" in page


def test_unexpected_errors_are_shown_too(world, signed_in, monkeypatch):  # noqa: F811
    def boom(*args, **kwargs):
        raise KeyError("surprise")

    monkeypatch.setattr("community_insights.views.dashboard.add_project", boom)
    page = signed_in.post("/dashboard/", {"target": "o/x"}, follow=True).content.decode()
    assert "Unexpected error" in page and "KeyError" in page


def test_failed_jobs_link_to_their_error(world, signed_in):  # noqa: F811
    from community_insights.models import FetchJob

    FetchJob.objects.filter(status="failed").update(
        message="GitHub rejected the token.", error_code="InvalidAPIToken"
    )
    page = signed_in.get("/dashboard/downloads/").content.decode()
    assert errors.InvalidAPIToken.docs_url() in page


def test_progress_errors_are_json_with_what_to_do(world, signed_in, monkeypatch):  # noqa: F811
    import json

    def broken(repositories):
        raise errors.GitHubUnreachable("down")

    monkeypatch.setattr("community_insights.pipeline.completeness", broken)
    response = signed_in.get(f"/s/{world['project'].pk}/progress.json")
    assert response.status_code == 500
    error = json.loads(response.content)["error"]
    assert error["title"] == "GitHub cannot be reached" and error["detail"] == "down"
    assert error["docs_url"] == errors.GitHubUnreachable.docs_url()
