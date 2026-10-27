"""The tag of Horizon Europe next to locations, chosen in the profile, and in queries."""

import pytest

from community_insights.models import Profile

pytestmark = pytest.mark.django_db

TAG = b">Horizon Europe</span>"


def show_tag(user, shown=True):
    """Show or hide the tag of Horizon Europe in the profile."""
    profile = Profile.of(user)
    profile.show_horizon_europe = shown
    profile.save()


def test_the_profile_checkbox_is_saved(world, signed_in):
    """The profile checkbox is saved."""
    signed_in.post("/dashboard/github/", {"action": "profile", "show_horizon_europe": "on"})
    assert Profile.of(world["user"]).show_horizon_europe
    signed_in.post("/dashboard/github/", {"action": "profile"})
    assert not Profile.of(world["user"]).show_horizon_europe


def test_the_checkbox_is_on_the_profile_form(world, signed_in):
    """The checkbox is on the profile form."""
    assert b'name="show_horizon_europe"' in signed_in.get("/dashboard/github/").content


def test_no_tag_unless_chosen(world, signed_in):
    """No tag unless chosen."""
    page = signed_in.get(f"/s/{world['project'].pk}/contributors/").content
    assert b"Berlin" in page
    assert TAG not in page


def test_tag_next_to_the_location_of_contributors(world, signed_in):
    """Tag next to the location of contributors."""
    show_tag(world["user"])
    page = signed_in.get(f"/s/{world['project'].pk}/contributors/").content
    assert b"Berlin" in page
    assert TAG in page
    assert b'title="DE: a country of Horizon Europe"' in page


def test_tag_on_the_page_of_a_person(world, signed_in):
    """Tag on the page of a person."""
    show_tag(world["user"])
    assert TAG in signed_in.get(f"/s/{world['project'].pk}/people/bob/").content


def test_no_tag_for_people_outside(world, signed_in):
    """No tag for people outside."""
    from community_insights.models import Person

    Person.objects.filter(login="bob").update(location="New York")
    show_tag(world["user"])
    page = signed_in.get(f"/s/{world['project'].pk}/people/bob/").content
    assert b"New York" in page
    assert TAG not in page


def test_visitors_see_no_tag(world, client):
    """Visitors see no tag."""
    page = client.get("/s/o~r/people/bob/").content
    assert b"Berlin" in page
    assert TAG not in page


def test_query_with_horizon_europe_and_country(world, signed_in):
    """Query with horizon europe and country."""
    url = f"/s/{world['project'].pk}/contributors/"
    page = signed_in.get(
        url, {"where": 'user_horizon_europe and user_country == "de"'}
    ).content.decode()
    assert ">bob</a>" in page
    assert ">carol</a>" not in page
    grouped = signed_in.get(url, {"group": "user_country"}).content.decode()
    assert "<td>DE</td>" in grouped
    assert "<td>(none)</td>" in grouped
