"""The places of locations are found once and kept; a changed location is found again."""

import pytest

from community_insights.locations.found import Found
from community_insights.locations.locator import Locator, known, only_country
from community_insights.models import Location, Person
from community_insights.sync import store

pytestmark = pytest.mark.django_db


class FakeSearch:
    """Nominatim that answers from a table and counts the questions."""

    def __init__(self, answers=None):
        """A fake.

        Args:
            answers: The answer to each location; None for the others.
        """
        self.answers = answers or {}
        self.asked = []

    def search(self, text):
        """The answer of the table.

        Args:
            text: The location.

        Returns:
            The answer.
        """
        self.asked.append(text)
        return self.answers.get(text)


def test_geonames_first_nominatim_only_when_needed():
    """Berlin is known offline; a small town and an unknown place are asked for."""
    search = FakeSearch(
        {
            "Kleinkleckersdorf, Germany": Found(
                "DE", "", "Kleinkleckersdorf", 50.0, 10.0, "nominatim"
            )
        }
    )
    found = Locator(search).locate(["Berlin", "Germany", "Kleinkleckersdorf, Germany", "Mars"])
    assert search.asked == ["Kleinkleckersdorf, Germany", "Mars"]
    assert found["Berlin"].city == "Berlin" and found["Germany"].city == ""
    assert found["Kleinkleckersdorf, Germany"].source == "nominatim"
    assert found["Mars"] is None


def test_each_location_is_found_once():
    """The second time, nothing is asked: the database knows, also what is not found."""
    search = FakeSearch()
    Locator(search).locate(["Mars", "Berlin"])
    again = FakeSearch()
    found = Locator(again).locate(["Mars", "Berlin", "  ", ""])
    assert again.asked == []
    assert found["Mars"] is None and found["Berlin"].country == "DE"
    assert Location.objects.get(text="Mars").country == ""


def test_a_changed_location_is_found_again(user):
    """Ann moves from Berlin to Cardiff: her new location is found, the old one is kept."""
    Locator().locate(["Berlin"])
    Locator().locate(["Cardiff, Wales"])
    assert set(Location.objects.values_list("text", flat=True)) == {"Berlin", "Cardiff, Wales"}
    assert Location.objects.get(text="Cardiff, Wales").region == "WLS"


def test_nominatim_must_agree_with_the_country():
    """A place of Nominatim in another country than GeoNames found is left out."""
    search = FakeSearch({"Ulm, Germany": Found("US", "", "Ulm", 1.0, 1.0, "nominatim")})
    found = Locator(search).locate(["Ulm, Germany"])
    assert found["Ulm, Germany"].country == "DE" and found["Ulm, Germany"].source == "geonames"


def test_a_limit_of_questions_per_fetch():
    """Beyond the limit, GeoNames alone decides; the rest waits for the next fetch."""
    search = FakeSearch()
    Locator(search, most=1).locate(["Mars", "Venus"])
    assert search.asked == ["Mars"]


def test_only_countries_and_regions_are_not_asked_for():
    """Names of countries, regions and states need no place."""
    assert only_country("Wales, UK") and only_country("Texas, USA") and only_country("DE")
    assert not only_country("Ulm, Germany")


def test_pages_read_without_writing():
    """A page uses what is kept and finds the rest offline, without keeping it."""
    Location.objects.create(text="Somewhere", country="FR", source="nominatim")
    found = known(["Somewhere", "Berlin", ""])
    assert found["Somewhere"].country == "FR" and found["Berlin"].country == "DE"
    assert not Location.objects.filter(text="Berlin").exists()


def test_the_fetch_locates_the_people_of_a_repository(synced):
    """After the people are read, their locations are kept (bob is in Berlin)."""
    assert Location.objects.get(text="Berlin").country == "DE"
    Person.objects.filter(login="bob").update(location="Cardiff")
    store.locate_people(synced)
    assert Location.objects.get(text="Cardiff").region == "WLS"


def test_the_worker_of_its_own_locates_in_another_process(synced, settings, monkeypatch):
    """The worker stays small: it runs manage.py locate; a failure is no failure of the fetch."""
    calls = []

    def run(command, **kwargs):
        """Fail like a broken process."""
        calls.append(command)
        raise store.subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(store.subprocess, "run", run)
    settings.FETCH_WORKER = "external-http-container"
    store.locate_people(synced)
    assert calls[0][-2:] == ["locate", str(synced.pk)]


def test_the_command_locate(synced, capsys):
    """manage.py locate finds the places of the people of repositories."""
    from django.core.management import call_command

    Location.objects.all().delete()
    call_command("locate", synced.pk)
    assert "1 locations known" in capsys.readouterr().out
    assert Location.objects.filter(text="Berlin").exists()


def test_the_command_locate_with_a_wrong_number(db):
    """An unknown repository is an error of the command."""
    from django.core.management import call_command
    from django.core.management.base import CommandError

    with pytest.raises(CommandError):
        call_command("locate", 999)


def test_unused_locations_are_cleaned_up(synced):
    """A location nobody has any more is deleted with the unused data."""
    from community_insights.cleanup import clear_unused

    Location.objects.create(text="Old place", country="DE")
    clear_unused(90)
    assert not Location.objects.filter(text="Old place").exists()
    assert Location.objects.filter(text="Berlin").exists()
