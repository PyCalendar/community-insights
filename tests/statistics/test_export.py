"""The data behind the statistics as CSV, JSON and ODS."""

import csv
import io

import pytest

from community_insights import export, stats
from community_insights.classify import Classifier
from community_insights.models import Repository

pytestmark = pytest.mark.django_db


def test_response_table_matches_the_statistics(world):  # noqa: F811
    alice = world["user"]
    names = [c.name for c in alice.classes.all()]
    rows = export.responses(Repository.objects.all(), Classifier(alice), names)
    pr1 = next(r for r in rows if r["kind"] == "pr" and r["number"] == 1)
    assert pr1["seconds_bot"] == 600 and pr1["seconds_collaborator_or_higher"] == 7200
    assert pr1["seconds_external"] is None  # the author's own comment does not count
    assert pr1["seconds_any"] == 600 and pr1["responded"] == 1
    silent = next(r for r in rows if r["kind"] == "issue" and r["number"] == 2)
    assert silent["responded"] == 0 and silent["observed_seconds"] > 0  # censored
    entries = stats.response_entries(Repository.objects.all(), Classifier(alice))
    exported = sorted(r["seconds_bot"] for r in rows if r["kind"] == "pr" and r["seconds_bot"])
    assert exported == sorted(e["bot"] for e in entries["pr"] if "bot" in e)


def test_csv_is_readable(world, signed_in):  # noqa: F811
    pk = world["project"].pk
    for table in export.TABLES:
        response = signed_in.get(f"/s/{pk}/data/{table}.csv")
        assert response.status_code == 200 and "attachment" in response["Content-Disposition"]
        rows = list(csv.DictReader(io.StringIO(response.content.decode())))
        assert rows, table
    assert signed_in.get(f"/s/{pk}/data/secrets.csv").status_code == 404
    assert signed_in.get(f"/s/{pk}/data/items.xml").status_code == 404


def test_ods_downloads_have_the_source_data(world, signed_in):  # noqa: F811
    import io

    from odf.opendocument import load
    from odf.table import Table

    pk = world["project"].pk

    def sheets(url):
        response = signed_in.get(url)
        assert response.status_code == 200, url
        assert response["Content-Type"] == "application/vnd.oasis.opendocument.spreadsheet"
        document = load(io.BytesIO(response.content))
        return [t.getAttribute("name") for t in document.spreadsheet.getElementsByType(Table)]

    assert sheets(f"/s/{pk}/data/responses.ods") == ["responses", "items", "events", "about"]
    assert sheets(f"/s/{pk}/data/commits.ods") == ["commits", "about"]
    assert sheets(f"/s/{pk}/data/contributors.ods") == [
        "contributors",
        "items",
        "events",
        "commits",
        "about",
    ]
    query = sheets(f"/s/{pk}/contributors.ods?where=prs_opened+%3E+0")
    assert query == ["query result", "contributors", "items", "events", "commits", "about"]
    assert signed_in.get(f"/s/{pk}/contributors.csv").status_code == 200
    assert signed_in.get(f"/s/{pk}/data/items.xlsx").status_code == 404


def test_ods_numbers_are_numbers():
    import io

    from odf.opendocument import load
    from odf.table import TableCell

    from community_insights import spreadsheet

    content = spreadsheet.to_ods([("t", [{"n": 3, "x": 1.5, "s": "a", "b": True, "none": None}])])
    cells = load(io.BytesIO(content)).spreadsheet.getElementsByType(TableCell)
    types = [c.getAttribute("valuetype") for c in cells[5:]]
    assert types == ["float", "float", "string", "float", "string"]
    assert spreadsheet.to_ods([("empty", [])])
