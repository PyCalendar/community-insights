"""The data behind the statistics as CSV, JSON and ODS."""

import csv
import io

import pytest

from community_insights import export, stats
from community_insights.classify import Classifier
from community_insights.models import Repository

pytestmark = pytest.mark.django_db


def test_response_table_matches_the_statistics(world):  # noqa: F811
    """Response table matches the statistics."""
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
    """Csv is readable."""
    pk = world["project"].pk
    for table in export.TABLES:
        response = signed_in.get(f"/s/{pk}/data/{table}.csv")
        assert response.status_code == 200 and "attachment" in response["Content-Disposition"]
        rows = list(csv.DictReader(io.StringIO(response.content.decode())))
        assert rows, table
    assert signed_in.get(f"/s/{pk}/data/secrets.csv").status_code == 404
    assert signed_in.get(f"/s/{pk}/data/items.xml").status_code == 404


def test_ods_downloads_have_the_source_data(world, signed_in):  # noqa: F811
    """Ods downloads have the source data."""
    import io

    from odf.opendocument import load
    from odf.table import Table

    pk = world["project"].pk

    def sheets(url):
        """The names of the sheets of the ODS of an address."""
        response = signed_in.get(url)
        assert response.status_code == 302 and response["Location"].startswith("/documents/"), url
        file = signed_in.get(response["Location"] + "download/")
        assert file.status_code == 200, url
        assert file["Content-Type"] == "application/vnd.oasis.opendocument.spreadsheet"
        document = load(io.BytesIO(b"".join(file.streaming_content)))
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
    query = sheets(f"/s/{pk}/contributors.ods?where=prs_total+%3E+0")
    assert query == ["query result", "contributors", "items", "events", "commits", "about"]
    assert signed_in.get(f"/s/{pk}/contributors.csv").status_code == 200
    assert signed_in.get(f"/s/{pk}/data/items.xlsx").status_code == 404


def test_ods_numbers_are_numbers():
    """Ods numbers are numbers."""
    import io

    from odf.opendocument import load
    from odf.table import TableCell

    from community_insights import spreadsheet

    content = spreadsheet.to_ods([("t", [{"n": 3, "x": 1.5, "s": "a", "b": True, "none": None}])])
    cells = load(io.BytesIO(content)).spreadsheet.getElementsByType(TableCell)
    types = [c.getAttribute("valuetype") for c in cells[5:]]
    assert types == ["float", "float", "string", "float", "string"]
    assert spreadsheet.to_ods([("empty", [])])


def test_parquet_keeps_the_types_and_says_what_it_is(world, signed_in):  # noqa: F811
    """Parquet has numbers, times in UTC, and the facts of the export as metadata."""
    import json

    import pandas
    import pyarrow.parquet

    pk = world["project"].pk
    for table in export.TABLES:
        response = signed_in.get(f"/s/{pk}/data/{table}.parquet")
        assert response.status_code == 200 and "attachment" in response["Content-Disposition"]
        assert response["Content-Type"] == "application/vnd.apache.parquet"
        frame = pandas.read_parquet(io.BytesIO(response.content))
        assert len(frame), table
        about = json.loads(
            pyarrow.parquet.read_schema(io.BytesIO(response.content)).metadata[
                b"community-insights"
            ]
        )
        assert about["table"] == table and about["repositories"] == ["o/r"]
    responses = pandas.read_parquet(
        io.BytesIO(signed_in.get(f"/s/{pk}/data/responses.parquet").content)
    )
    assert str(responses["created_at"].dtype) == "datetime64[ns, UTC]"
    assert responses["closed_at"].isna().any(), "an open item has no time of closing"
    assert pandas.api.types.is_numeric_dtype(responses["observed_seconds"])


def test_parquet_of_no_rows():
    """An empty table is a valid Parquet file without rows."""
    import pandas

    assert len(pandas.read_parquet(io.BytesIO(export.to_parquet([], {"table": "items"})))) == 0


def test_csv_keeps_the_values_as_they_are():
    """Whole numbers stay whole, missing values are empty, as before pandas."""
    rows = [{"n": 1, "s": None, "f": 1.5}, {"n": 2, "s": 3.0, "f": None}]
    assert export.to_csv(rows) == "n,s,f\n1,,1.5\n2,3.0,\n"


def test_the_data_links_offer_parquet(world, signed_in):  # noqa: F811
    """The section Data and sources links the Parquet files."""
    pk = world["project"].pk
    page = signed_in.get(f"/s/{pk}/").content.decode()
    assert f"/s/{pk}/data/responses.parquet" in page


def test_csv_quotes_commas_quotes_and_line_breaks():
    """Titles with commas, quotes and new lines stay one cell."""
    rows = [{"title": 'Fix "a", b\nand c', "n": 1}]
    text = export.to_csv(rows)
    assert list(csv.DictReader(io.StringIO(text))) == [{"title": 'Fix "a", b\nand c', "n": "1"}]


def test_parquet_of_columns_without_values_and_without_times():
    """A class nobody responded as, and times that are all missing, still make a file."""
    import pandas

    rows = [
        {"number": 1, "seconds_bot": None, "closed_at": "", "title": "a"},
        {"number": 2, "seconds_bot": None, "closed_at": "", "title": "b"},
    ]
    frame = pandas.read_parquet(io.BytesIO(export.to_parquet(rows, {"table": "responses"})))
    assert frame["seconds_bot"].isna().all() and frame["closed_at"].isna().all()
    assert list(frame["number"]) == [1, 2] and list(frame["title"]) == ["a", "b"]


def test_parquet_keeps_text_that_looks_like_a_number():
    """A login such as 007 stays text."""
    import pandas

    data = export.to_parquet([{"login": "007"}, {"login": "bob"}], {})
    assert list(pandas.read_parquet(io.BytesIO(data))["login"]) == ["007", "bob"]


@pytest.mark.parametrize("extension", ["parquet", "PARQUET", "parq", ""])
def test_only_known_extensions_are_exported(world, signed_in, extension):  # noqa: F811
    """Other extensions are not found."""
    status = signed_in.get(f"/s/{world['project'].pk}/data/items.{extension}").status_code
    assert status == (200 if extension == "parquet" else 404)
