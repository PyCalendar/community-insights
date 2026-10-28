"""Classes of people and their rules."""

import pytest
from django.contrib.auth import get_user_model

from community_insights import stats
from community_insights.classify import Classifier
from community_insights.models import ClassRule, PersonClass, Repository

pytestmark = pytest.mark.django_db


def test_custom_class_by_handle_wins_by_its_order(synced, user):
    """Custom class by handle wins by its order."""
    maintainers = PersonClass.objects.create(user=user, name="maintainers")
    maintainers.top()
    maintainers.rules.create(kind=ClassRule.HANDLE, value="DAVE")
    entries = stats.response_entries(Repository.objects.all(), Classifier(user))
    assert entries["issue"][0] == {"maintainers": 2 * 86400}


def test_class_rules_pattern_and_location(user):
    """Class rules pattern and location."""
    robots = PersonClass.objects.create(user=user, name="robots")
    robots.rules.create(kind=ClassRule.PATTERN, value="*-robot")
    robots.top()
    berliners = PersonClass.objects.create(user=user, name="berliners")
    berliners.rules.create(kind=ClassRule.LOCATION, value="berlin")
    berliners.top()
    classify = Classifier(user, {"bob": "Berlin, Germany"})
    assert classify("bob", "none", False).name == "berliners"
    assert classify("x-robot", "none", False).name == "robots"
    assert classify("eve", "none", False).name == "external"
    assert classify("eve", "owner", False).name == "collaborator or higher"


def test_classes_page_creates_class_and_rule(user, signed_in):
    """Classes page creates class and rule."""
    signed_in.post(
        "/dashboard/classes/", {"action": "add_class", "name": "maintainers", "color": "#112233"}
    )
    created = PersonClass.objects.get(name="maintainers")
    signed_in.post(
        "/dashboard/classes/",
        {"action": "add_rule", "id": created.pk, "kind": "handle", "value": "x y"},
    )
    assert created.rules.get().value == "x y"
    signed_in.post("/dashboard/classes/", {"action": "up", "id": created.pk})
    assert list(user.classes.values_list("name", flat=True))[-2] == "maintainers"


def test_class_rules_with_unknown_kind_are_refused(world, signed_in):  # noqa: F811
    """Class rules with unknown kind are refused."""
    pc = world["user"].classes.first()
    response = signed_in.post(
        "/dashboard/classes/", {"action": "add_rule", "id": pc.pk, "kind": "evil"}, follow=True
    )
    assert b"Not saved" in response.content


def test_classes_of_others_cannot_be_changed(world, client):  # noqa: F811
    """Classes of others cannot be changed."""
    other = get_user_model().objects.create_user("o", "o@example.org", "pw")
    client.force_login(other)
    pc = world["user"].classes.first()
    client.post("/dashboard/classes/", {"action": "delete_class", "id": pc.pk})
    assert PersonClass.objects.filter(pk=pc.pk).exists()


def test_a_class_is_renamed_and_recoloured_in_place(user, signed_in):
    """A class is renamed and recoloured in place."""
    bot = user.classes.get(name="bot")
    signed_in.post(
        "/dashboard/classes/",
        {"action": "edit_class", "id": bot.pk, "name": " robots ", "color": "#ABCDEF"},
    )
    bot.refresh_from_db()
    assert (bot.name, bot.color) == ("robots", "#abcdef")


@pytest.mark.parametrize(
    ("name", "color", "error"),
    [
        ("external", "#123456", b"Class name taken"),
        ("robots", "red", b"Invalid colour"),
        ("robots", "#12345", b"Invalid colour"),
    ],
)
def test_a_class_keeps_its_name_and_colour_on_errors(user, signed_in, name, color, error):
    """A class keeps its name and colour on errors."""
    bot = user.classes.get(name="bot")
    response = signed_in.post(
        "/dashboard/classes/",
        {"action": "edit_class", "id": bot.pk, "name": name, "color": color},
        follow=True,
    )
    assert error in response.content
    bot.refresh_from_db()
    assert (bot.name, bot.color) == ("bot", "#9ccc9c")


def test_a_new_class_needs_a_new_name_and_a_colour(user, signed_in):
    """A new class needs a new name and a colour."""
    taken = signed_in.post(
        "/dashboard/classes/", {"action": "add_class", "name": "bot"}, follow=True
    )
    assert b"Class name taken" in taken.content
    wrong = signed_in.post(
        "/dashboard/classes/", {"action": "add_class", "name": "x", "color": "x"}, follow=True
    )
    assert b"Invalid colour" in wrong.content
    assert user.classes.count() == 3


def test_the_classes_are_put_in_a_new_order(user, signed_in):
    """The classes are put in a new order."""
    ids = [str(pk) for pk in user.classes.values_list("pk", flat=True)]
    signed_in.post("/dashboard/classes/", {"action": "order", "order": ids[::-1]})
    assert [str(pk) for pk in user.classes.values_list("pk", flat=True)] == ids[::-1]


@pytest.mark.parametrize("change", ["missing", "twice", "other"])
def test_an_order_must_name_each_class_once(user, signed_in, change):
    """An order must name each class once."""
    ids = [str(pk) for pk in user.classes.values_list("pk", flat=True)]
    wrong = {"missing": ids[:-1], "twice": ids + ids[:1], "other": [*ids[:-1], "99999"]}[change]
    response = signed_in.post(
        "/dashboard/classes/", {"action": "order", "order": wrong}, follow=True
    )
    assert b"Invalid order of the classes" in response.content
    assert [str(pk) for pk in user.classes.values_list("pk", flat=True)] == ids


def test_the_classes_page_can_be_ordered_by_dragging(user, signed_in):
    """The classes page can be ordered by dragging."""
    page = signed_in.get("/dashboard/classes/").content.decode()
    assert 'data-sort-list data-sort-form="class-order"' in page and "data-sort-handle" in page
    assert 'id="class-order"' in page
    assert 'name="action" value="edit_class"' in page
    assert "vendor/sortable/Sortable.min.js" in page and "js/sortable-order.js" in page


def test_the_classes_of_the_site_are_hidden_not_deleted(user, signed_in):
    """The classes of the site are hidden not deleted."""
    from community_insights.classify import visible_classes

    bot = user.classes.get(name="bot")
    assert bot.preset == "bot" and not bot.hidden
    refused = signed_in.post(
        "/dashboard/classes/", {"action": "delete_class", "id": bot.pk}, follow=True
    )
    assert b"Class cannot be deleted" in refused.content
    assert user.classes.filter(pk=bot.pk).exists()
    signed_in.post("/dashboard/classes/", {"action": "hide", "id": bot.pk})
    bot.refresh_from_db()
    assert bot.hidden
    assert "bot" not in [c.name for c in visible_classes(user)]
    page = signed_in.get("/dashboard/classes/").content.decode()
    assert "Still sorts people" in page and 'value="show"' in page
    signed_in.post("/dashboard/classes/", {"action": "show", "id": bot.pk})
    bot.refresh_from_db()
    assert not bot.hidden


def test_a_hidden_class_still_sorts_people(synced, user, signed_in):
    """A hidden class still sorts people."""
    from community_insights.models import Project

    user.classes.filter(name="bot").update(hidden=True)
    entries = stats.response_entries(Repository.objects.all(), Classifier(user))
    assert all("external" not in e or e["external"] != 600 for e in entries["pr"]), (
        "the bot's answer after 10 minutes is no external response"
    )
    page = signed_in.get(f"/s/{Project.objects.get().pk}/").content.decode()
    table = page[page.index('id="fits-pr"') :]
    assert "<td>bot</td>" not in table


def test_own_classes_are_deleted_and_presets_link_their_explanation(user, signed_in):
    """Own classes are deleted and presets link their explanation."""
    own = PersonClass.objects.create(user=user, name="maintainers")
    page = signed_in.get("/dashboard/classes/").content.decode()
    assert "reference/classes.html#class-bot" in page
    assert "reference/classes.html#class-collaborator" in page
    assert "reference/classes.html#class-external" in page
    signed_in.post("/dashboard/classes/", {"action": "delete_class", "id": own.pk})
    assert not PersonClass.objects.filter(pk=own.pk).exists()


def test_the_migration_marks_the_classes_of_the_site(user):
    """The migration marks the classes of the site."""
    from importlib import import_module

    from django.apps import apps

    user.classes.update(preset="")
    import_module("community_insights.migrations.0006_class_preset_hidden").mark_presets(apps, None)
    assert dict(user.classes.values_list("name", "preset")) == {
        "bot": "bot",
        "collaborator or higher": "collaborator",
        "external": "external",
    }


def test_the_classes_page_links_the_kinds_of_rules(user, signed_in):
    """The classes page links the kinds of rules."""
    page = signed_in.get("/dashboard/classes/").content.decode()
    assert "reference/class-rules.html#rule-bot" in page
    assert "reference/class-rules.html#rule-association" in page
    assert "reference/class-rules.html#rule-any" in page
    assert "What the kinds of rules mean" in page
