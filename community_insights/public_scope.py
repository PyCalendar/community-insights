"""The public address of projects: their pages for everybody, without the numbers of the site.

A project is shown at ``/s/<number>/`` to its owner only. When all of its repositories are
public, the same pages exist for everybody at ``/s/<owner~name+...>/``; that address is
preferred: links use it, and the address with the number leads there.
"""

from .models import Repository


def public_scope(projects) -> str | None:
    """The public scope with the same repositories as projects, for an address.

    An organisation or user whose known public repositories are all in the projects is
    written as its login (``plone``), the other repositories as ``owner~name``, joined with
    ``+``.

    Args:
        projects: The projects.

    Returns:
        The text of the scope; None if a project is private, or has a private repository, or
        none has a repository.
    """
    projects = list(projects)
    if not projects or any(p.is_private for p in projects):
        return None
    repositories = list(Repository.objects.filter(projects__in=projects).distinct())
    if not repositories or any(r.is_private for r in repositories):
        return None
    names = {r.full_name for r in repositories}
    parts = []
    owners = sorted({p.target for p in projects if "/" not in p.target}, key=str.lower)
    for owner in owners:
        known = Repository.objects.filter(is_private=False, owner_login__iexact=owner)
        found = {r.full_name: r.owner_login for r in known}
        if found and set(found) <= names:
            parts.append(next(iter(found.values())))
            names -= set(found)
    parts += [name.replace("/", "~") for name in sorted(names, key=str.lower)]
    return "+".join(parts)


def address_of(project) -> str:
    """The scope of the pages of a project in addresses: public if it can be, else its number.

    Args:
        project: The project.

    Returns:
        Such as ``collective~icalendar``, or ``3`` for a project with a private repository.
    """
    return public_scope([project]) or str(project.pk)
