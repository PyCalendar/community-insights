"""What people did: counts, contributors, commits."""

from datetime import UTC

import pytest

from community_insights import export, stats
from community_insights.classify import Classifier
from community_insights.models import Repository
from community_insights.sync import read_repository, store_repository

from ..fakes import FakeClient, repo

pytestmark = pytest.mark.django_db


def test_counts_and_contributors(synced, user):
    """Counts and contributors."""
    counts = stats.counts(Repository.objects.all())
    assert counts["prs"]["merged"] == 1 and counts["prs"]["open"] == 1
    people = {p.login: p for p in stats.contributors(Repository.objects.all(), Classifier(user))}
    assert people["bob"].prs_opened == 1 and people["bob"].prs_merged == 1
    assert people["bob"].location == "Berlin"
    assert people["maint"].reviews == 1
    assert people["maint"].median_response == 7200
    assert people["ci[bot]"].klass == "bot"


def test_closed_unmerged_pull_requests(world):  # noqa: F811
    """Closed unmerged pull requests."""
    counts = stats.counts(Repository.objects.all())
    assert counts["prs"] == {"total": 3, "open": 1, "merged": 1, "closed": 1}
    assert counts["issues"] == {"total": 2, "open": 2, "closed": 0}


def test_commits_are_contributions(user):  # noqa: F811
    """Commits are contributions."""
    from community_insights.models import Commit

    from ..fakes import commit

    repository = store_repository(repo("o/c"))
    client = FakeClient(
        commits=[
            commit("a" * 40, "bob", "2026-01-05T10:00:00Z"),
            commit("b" * 40, "bob", "2026-01-06T10:00:00Z"),
            commit("c" * 40, None, "2026-01-07T10:00:00Z", name="Somebody"),
        ]
    )
    assert "3 commits read" in read_repository(client, repository)
    assert Commit.objects.count() == 3
    repository.refresh_from_db()
    assert repository.commits_total == 3 and repository.commits_synced_until is not None
    assert "0 commits read" in read_repository(client, repository), "only new commits"
    people = {p.login: p for p in stats.contributors(Repository.objects.filter(pk=repository.pk))}
    assert people["bob"].commits == 2 and people["bob"].activity == 2
    kinds = [kind for _, kind in stats.activity_of([repository], "bob")]
    assert kinds == ["commit", "commit"]
    rows = export.commits([repository])
    assert [r["author"] for r in rows] == ["bob", "bob", ""] and rows[2][
        "author_name"
    ] == "Somebody"


def test_response_times_of_a_person_by_month(world, signed_in):  # noqa: F811
    """Response times of a person by month."""
    months = stats.responses_by_month(Repository.objects.all(), "maint", UTC)
    assert months == {(2026, 1): [7200.0]}
    assert stats.responses_by_month(Repository.objects.all(), "bob", UTC) == {}, (
        "own items do not count"
    )
    pk = world["project"].pk
    for login in ("maint", "bob"):
        response = signed_in.get(f"/s/{pk}/chart/responses.svg?login={login}")
        assert response.status_code == 200 and b"<svg" in response.content


def test_the_query_field_has_examples_that_keep_the_time_range(synced, signed_in):
    """The query field has examples that keep the time range."""
    from community_insights.models import Project

    pk = Project.objects.get().pk
    page = signed_in.get(f"/s/{pk}/contributors/?since=2026-01-01").content.decode()
    assert "Who opened a pull request, the most merged first" in page
    assert 'href="?where=prs_total+%3E+0&amp;sort=-prs_merged&amp;since=2026-01-01"' in page
    assert "Most commits in the last month" in page
    assert 'href="?where=commits_total+%3E+0&amp;sort=-commits_total&amp;last=30"' in page, (
        "the time range is a part of the example"
    )


def test_parts_are_shown_with_their_total(synced, signed_in):
    """Parts are shown with their total."""
    from community_insights.models import Project

    pk = Project.objects.get().pk
    page = signed_in.get(
        f"/s/{pk}/contributors/?columns=user_handle+prs_total+prs_merged+issues_open"
    ).content.decode()
    assert '1<span class="text-muted">/1</span>' in page, "bob: 1 of 1 pull requests merged"
    grouped = signed_in.get(f"/s/{pk}/contributors/?group=user_class").content.decode()
    assert "/" in grouped[grouped.index("<h2") :]


def test_the_headers_explain_the_variables_in_a_new_tab(synced, signed_in):
    """The headers explain the variables in a new tab."""
    from community_insights.models import Project

    pk = Project.objects.get().pk
    page = signed_in.get(f"/s/{pk}/contributors/").content.decode()
    assert (
        'href="https://community-insights.readthedocs.io/en/latest/reference/query-variables.html'
        '#hours-to-respond" target="_blank" rel="noopener"' in page
    )
    assert 'title="Sort by: pull requests opened and merged"' in page


def test_the_headers_sort_the_table(synced, signed_in):
    """The headers sort the table."""
    from community_insights.models import Project

    pk = Project.objects.get().pk
    page = signed_in.get(f"/s/{pk}/contributors/?sort=-prs_total&last=30").content.decode()
    assert 'href="?where=&amp;sort=-commits_total&amp;columns=' in page, (
        "numbers: the biggest first"
    )
    assert "sort=user_handle" in page, "text: from A"
    assert 'aria-sort="descending"' not in page or "▼" in page
    assert "last=30" in page[page.index("sort=-commits_total") :][:300], "the time range stays"
    sorted_by = signed_in.get(f"/s/{pk}/contributors/?sort=-prs_merged").content.decode()
    header = sorted_by[sorted_by.index('aria-sort="descending"') :][:400]
    assert "prs_merged" in header and "▼" in header
    assert "sort=prs_merged" in header, "a second click sorts the other way"


def test_the_names_of_the_columns_switch_to_words(synced, signed_in):
    """The names of the columns switch to words."""
    from community_insights.models import Project

    page = signed_in.get(f"/s/{Project.objects.get().pk}/contributors/").content.decode()
    assert 'data-column-names="#contributors-table"' in page
    assert 'id="contributors-table" data-names="variables"' in page
    assert '<span class="name-words">pull requests opened and merged</span>' in page
    assert "js/column-names.js" in page


def test_an_unknown_sort_is_shown_as_an_error(synced, signed_in):
    """An unknown sort is shown as an error, and the headers still sort."""
    from community_insights.models import Project

    response = signed_in.get(f"/s/{Project.objects.get().pk}/contributors/?sort=response")
    assert response.status_code == 200
    assert "There is no variable" in response.content.decode()


def test_the_query_runs_without_loading_the_page(world, signed_in):  # noqa: F811
    """htmx sends the query and puts only the result and the messages into the page."""
    pk = world["project"].pk
    page = signed_in.get(f"/s/{pk}/contributors/").content.decode()
    assert f'hx-get="/s/{pk}/contributors/"' in page
    assert 'hx-trigger="submit, change from:#group, change from:#chart"' in page
    assert 'hx-select="#query-result"' in page and 'hx-push-url="true"' in page
    assert 'hx-select-oob="#messages"' in page and '<div id="messages">' in page
    assert '<div id="query-result"' in page
    assert '<thead hx-boost="true" hx-push-url="true">' in page, "sorting without a reload"


def test_the_result_has_the_downloads_of_its_query(world, signed_in):  # noqa: F811
    """The downloads are part of the result, so they follow a query htmx ran."""
    pk = world["project"].pk
    page = signed_in.get(
        f"/s/{pk}/contributors/?where=prs_opened+>+0", HTTP_HX_REQUEST="true"
    ).content.decode()
    result = page[page.index('<div id="query-result"') :]
    assert f"/s/{pk}/contributors.csv?where=prs_opened" in result


def test_an_invalid_query_shows_its_error_in_the_messages(world, signed_in):  # noqa: F811
    """The error of a query is in the messages, which htmx puts into the page, too."""
    pk = world["project"].pk
    page = signed_in.get(
        f"/s/{pk}/contributors/?where=nonsense+>+1", HTTP_HX_REQUEST="true"
    ).content.decode()
    messages = page[page.index('<div id="messages">') : page.index('<div id="query-result"')]
    assert "nonsense" in messages
