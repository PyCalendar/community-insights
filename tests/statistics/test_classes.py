"""Classes of people and their rules."""

import pytest
from django.contrib.auth import get_user_model

from community_insights import stats
from community_insights.classify import Classifier
from community_insights.models import ClassRule, PersonClass, Repository

pytestmark = pytest.mark.django_db


def test_custom_class_by_handle_wins_by_its_order(synced, user):
    maintainers = PersonClass.objects.create(user=user, name="maintainers")
    maintainers.top()
    maintainers.rules.create(kind=ClassRule.HANDLE, value="DAVE")
    entries = stats.response_entries(Repository.objects.all(), Classifier(user))
    assert entries["issue"][0] == {"maintainers": 2 * 86400}


def test_class_rules_pattern_and_location(user):
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
    pc = world["user"].classes.first()
    response = signed_in.post(
        "/dashboard/classes/", {"action": "add_rule", "id": pc.pk, "kind": "evil"}, follow=True
    )
    assert b"Not saved" in response.content


def test_classes_of_others_cannot_be_changed(world, client):  # noqa: F811
    other = get_user_model().objects.create_user("o", "o@example.org", "pw")
    client.force_login(other)
    pc = world["user"].classes.first()
    client.post("/dashboard/classes/", {"action": "delete_class", "id": pc.pk})
    assert PersonClass.objects.filter(pk=pc.pk).exists()
