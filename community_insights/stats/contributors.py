"""Who did what: the contributors of repositories."""

from datetime import datetime

from ..models import Commit, Event, Item, Person
from .associations import more_privileged
from .contributor import Contributor
from .responses import responses_to
from .selection import events_in


def contributors(
    repositories, classifier=None, since: datetime | None = None, until: datetime | None = None
) -> list[Contributor]:
    """Everybody who did something in the time range, with what they did.

    Args:
        repositories: The repositories.
        classifier: Decides the class of each person; None leaves the class empty.
        since: The start of the time range, None for the beginning.
        until: The end of the time range, excluded; None for now.

    Returns:
        The contributors.
    """
    items = {
        pk: (kind, author.lower(), created, state, merged)
        for pk, kind, author, created, state, merged in Item.objects.filter(
            repository__in=repositories
        ).values_list("id", "kind", "author", "created_at", "state", "merged")
    }
    people: dict[str, Contributor] = {}

    def get(login: str) -> Contributor:
        return people.setdefault(login.lower(), Contributor(login))

    events = (
        events_in(Event.objects.filter(item__in=items.keys()), since, until)
        .order_by("at")
        .values_list("item_id", "actor", "kind", "at", "association")
    )
    associations: dict[str, str] = {}
    for pk, actor, kind, at, association in events.iterator():
        if association:
            key = actor.lower()
            associations[key] = more_privileged(associations.get(key, ""), association)
        kind_of_item, author, created, state, merged = items[pk]
        person = get(actor)
        person.first = min(person.first or at, at)
        person.last = max(person.last or at, at)
        person.months.add((at.year, at.month))
        pr = kind_of_item == Item.PR
        if kind == Event.OPENED:
            if pr:
                person.prs_opened += 1
                person.prs_merged += merged
                person.prs_closed += state == "closed" and not merged
                person.prs_open += state == "open"
            else:
                person.issues_opened += 1
                person.issues_closed += state == "closed"
                person.issues_open += state == "open"
        elif actor.lower() != author:
            if kind == Event.COMMENT:
                person.comments += 1
                (person.prs_commented if pr else person.issues_commented).add(pk)
            else:
                person.reviews += 1
                person.prs_reviewed.add(pk)
    for found in responses_to(
        Item.objects.filter(repository__in=repositories), since, until
    ).values():
        responded: set[str] = set()
        for response in found:  # their first response on each item of others
            if response.actor.lower() not in responded:
                responded.add(response.actor.lower())
                get(response.actor).delays.append(response.seconds)
    actions = Item.objects.filter(repository__in=repositories, closed_at__isnull=False)
    if since:
        actions = actions.filter(closed_at__gte=since)
    if until:
        actions = actions.filter(closed_at__lt=until)
    for author, merged, merged_by, created, closed in actions.values_list(
        "author", "merged", "merged_by", "created_at", "closed_at"
    ).iterator():
        if merged and merged_by:
            get(merged_by).merges += 1
        if merged and author:
            get(author).merge_days.append((closed - created).total_seconds() / 86400)
    commits = Commit.objects.filter(repository__in=repositories).exclude(author="")
    if since:
        commits = commits.filter(at__gte=since)
    if until:
        commits = commits.filter(at__lt=until)
    for login, at in commits.values_list("author", "at").iterator():
        person = get(login)
        person.commits += 1
        person.first = min(person.first or at, at)
        person.last = max(person.last or at, at)
        person.months.add((at.year, at.month))
    known = {
        p.login.lower(): p
        for p in Person.objects.filter(login__in=[c.login for c in people.values()])
    }
    for key, person in people.items():
        if key in known:
            person.name = known[key].name
            person.location = known[key].location
            person.avatar_url = known[key].avatar_url
        person.association = associations.get(key, "")
        if classifier:
            bot = known[key].is_bot if key in known else key.endswith("[bot]")
            chosen = classifier(person.login, associations.get(key, ""), bot)
            person.klass = chosen.name if chosen else ""
    return list(people.values())
