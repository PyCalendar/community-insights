from urllib.parse import urlencode

from django.conf import settings

from . import version


def links() -> dict:
    """The addresses of the code and the documentation (SOURCE_URL, DOCS_URL).

    Returns:
        The addresses of the documentation, the changelog, the code and new issues.
    """
    source = settings.SOURCE_URL.rstrip("/")
    docs = settings.DOCS_URL.rstrip("/") + "/"
    return {
        "documentation": docs,
        "changelog": f"{docs}changelog.html",
        "source": source,
        "issues": f"{source}/issues/new",
    }


BUG_REPORT = """**What happened?**


**What did you expect?**


**How can we see it?**
1.

---
Page: {page}
Version: {version}
Commit: {commit}
"""


def bug_report_url(request, build: dict) -> str:
    """A new GitHub issue with the page and the version filled in.

    The page is given without its query, which can contain a badge token or a search.

    Args:
        request: The request of the page.
        build: The build information: version and commit.

    Returns:
        The address of a new issue on GitHub.
    """
    body = BUG_REPORT.format(
        page=request.build_absolute_uri(request.path),
        version=build.get("version", ""),
        commit=build.get("commit", "") or "-",
    )
    return f"{links()['issues']}?{urlencode({'labels': 'bug', 'body': body})}"


THEMES = ("auto", "light", "dark")


def site(request):
    """Build information, links and the theme for every page.

    Build information, links for the footer, and the theme: the choice of the switch (cookie
    "theme") and the theme the charts are drawn in first; for "auto" static/js/theme.js switches
    them if the system is dark.

    Args:
        request: The request of the page.

    Returns:
        The variables for every template.
    """
    build = version.get()
    choice = request.COOKIES.get("theme", "auto")
    choice = choice if choice in THEMES else "auto"
    found = links()
    return {
        "build": {**build, **version.source_links(found["source"], build)},
        "links": found,
        "bug_report_url": bug_report_url(request, build),
        "theme_choice": choice,
        "private_repositories": settings.PRIVATE_REPOSITORIES,
        "theme_shown": "dark" if choice == "dark" else "light",
        "show_horizon_europe": shows_horizon_europe(request.user),
        "unread_messages": (
            request.user.messages.filter(read_at__isnull=True).count()
            if request.user.is_authenticated
            else 0
        ),
    }


def shows_horizon_europe(user) -> bool:
    """Whether the user chose to see the tag of Horizon Europe next to locations.

    Args:
        user: The user of the request, maybe a visitor.

    Returns:
        True if the profile says so; False for visitors.
    """
    if not user.is_authenticated:
        return False
    profile = getattr(user, "profile", None)
    return bool(profile and profile.show_horizon_europe)
