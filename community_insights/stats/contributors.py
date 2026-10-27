"""Who did what: the contributors of repositories."""

from datetime import datetime

from ..models import Commit, Event, Item, Person
from .contributor import Contributor
from .selection import events_in


def contributors(
    repositories, classifier=None, since: datetime | None = None, until: datetime | None = None
) -> list[Contributor]:
    """Everybody who did something in the time range, with what they did."""
    items = {
        pk: (kind, author.lower(), created, state, merged)
        for pk, kind, author, created, state, merged in Item.objects.filter(
            repository__in=repositories
        ).values_list("id", "kind", "author", "created_at", "state", "merged")
    }
    people: dict[str, Contributor] = {}

    def get(login: str) -> Contributor:
        return people.setdefault(login.lower(), Contributor(login))

    responded: set[tuple[int, str]] = set()
    events = (
        events_in(Event.objects.filter(item__in=items.keys()), since, until)
        .order_by("at")
        .values_list("item_id", "actor", "kind", "at", "association")
    )
    associations: dict[str, str] = {}
    for pk, actor, kind, at, association in events.iterator():
        if association:
            associations.setdefault(actor.lower(), association)
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
            else:
                person.reviews += 1
            if (pk, actor.lower()) not in responded:
                responded.add((pk, actor.lower()))
                person.delays.append(max((at - created).total_seconds(), 0))
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
        if classifier:
            bot = known[key].is_bot if key in known else key.endswith("[bot]")
            chosen = classifier(person.login, associations.get(key, ""), bot)
            person.klass = chosen.name if chosen else ""
    return list(people.values())
