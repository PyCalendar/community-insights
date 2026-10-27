"""The list of pull requests and issues."""

import pytest

pytestmark = pytest.mark.django_db


def rows(response) -> str:
    return response.content.decode()


def test_items_filtered_and_sorted(world, signed_in):  # noqa: F811
    pk = world["project"].pk
    page = rows(signed_in.get(f"/s/{pk}/items/"))
    assert "o/r#1" in page and "o/r#3" in page
    issues = rows(signed_in.get(f"/s/{pk}/items/?kind=issue"))
    assert "/issues/1" in issues and "/pull/1" not in issues
    merged = rows(signed_in.get(f"/s/{pk}/items/?state=merged"))
    assert "/pull/1" in merged and "/pull/2" not in merged
    silent = rows(signed_in.get(f"/s/{pk}/items/?responded=false"))
    assert "waiting" in silent and "/pull/1<" not in silent.replace('"', "<")
    answered = rows(signed_in.get(f"/s/{pk}/items/?responded=true"))
    assert "/pull/1" in answered and "waiting" not in answered
    by_response = rows(signed_in.get(f"/s/{pk}/items/?sort=response"))
    assert by_response.index("/pull/1") < by_response.index("/issues/1"), "10 minutes before 2 days"
    assert signed_in.get(f"/s/{pk}/items/?state=nonsense").status_code == 200
