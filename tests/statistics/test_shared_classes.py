"""Shared statistics carry the classes they were made with: ids such as maintainer-3."""

import pytest
from django.contrib.auth import get_user_model

from community_insights.classify import classes_by_ids, differs_from_default
from community_insights.errors import UnknownClasses
from community_insights.models import ClassRule, PersonClass, Project

pytestmark = pytest.mark.django_db


def test_a_class_has_an_id_of_its_name_and_number(user):
    """The id is the name and the number; it finds the class after a rename."""
    maintainers = PersonClass.objects.create(user=user, name="Core Maintainers")
    assert maintainers.ident == f"core-maintainers-{maintainers.pk}"
    assert classes_by_ids(maintainers.ident) == [maintainers]
    assert classes_by_ids(f"old-name-{maintainers.pk}") == [maintainers], "renamed"
    assert classes_by_ids(f"{maintainers.pk}, bot-{maintainers.pk}") == [maintainers] * 2


@pytest.mark.parametrize("text", ["nonsense", "x-99999"])
def test_unknown_ids(user, text):
    """An id that names no class is refused."""
    with pytest.raises(UnknownClasses):
        classes_by_ids(text)


def test_the_default_classes_are_not_carried(user):
    """Only classes that differ from the defaults go into addresses."""
    assert not differs_from_default(user)
    user.classes.filter(name="bot").update(hidden=True)
    assert differs_from_default(user)


def test_links_carry_the_classes_that_differ(synced, signed_in, user):
    """A user with own classes shares them in every link of the statistics."""
    pk = Project.objects.get().pk
    page = signed_in.get(f"/s/{pk}/").content.decode()
    assert "classes=" not in page, "the default classes need no parameter"
    maintainers = PersonClass.objects.create(user=user, name="maintainers")
    maintainers.rules.create(kind=ClassRule.HANDLE, value="dave")
    maintainers.top()
    page = signed_in.get(f"/s/{pk}/").content.decode()
    assert f"classes=maintainers-{maintainers.pk}" in page
    assert 'name="classes"' in page, "the form of the time range keeps them"


def test_a_shared_address_uses_the_classes_of_its_maker(synced, user, client):
    """Somebody else sees the numbers with the classes of the address, and a note."""
    maintainers = PersonClass.objects.create(user=user, name="maintainers", color="#123456")
    maintainers.rules.create(kind=ClassRule.HANDLE, value="dave")
    maintainers.top()
    idents = "+".join(c.ident for c in user.classes.all())
    other = get_user_model().objects.create_user("kim", "kim@example.org", "pw")
    client.force_login(other)
    page = client.get(f"/s/o~r/?classes={idents}").content.decode()
    assert "Classes of people of the shared address" in page
    assert "Use my own classes" in page
    table = page[page.index('id="fits-issue"') :]
    assert "<td>maintainers</td>" in table, "dave answered the issue as a maintainer"
    own = client.get("/s/o~r/").content.decode()
    assert "maintainers" not in own[own.index('id="fits-issue"') :]


def test_an_unknown_class_shows_an_error_and_the_own_classes(synced, client):
    """A deleted class is an error; the page shows the own classes, with its time range."""
    page = client.get("/s/o~r/?classes=gone-99999&last=30").content.decode()
    assert "Unknown classes" in page
    assert 'value="30"' in page, "the time range stays"


def test_badges_take_the_classes(synced, user, client):
    """A badge counts with the classes of its address."""
    maintainers = PersonClass.objects.create(user=user, name="maintainers")
    maintainers.rules.create(kind=ClassRule.HANDLE, value="maint")
    maintainers.top()
    content = client.get(f"/badge/s/o~r.svg?class=maintainers&classes={maintainers.ident}").content
    assert b"PR response p50 (maintainers)" in content and b"2h" in content
    assert client.get("/badge/s/o~r.svg?classes=gone-99999").status_code == 404
