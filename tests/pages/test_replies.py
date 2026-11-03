"""The page of replies, the pull requests and issues of a person, and the reply badges."""

import re

import pytest

from community_insights.models import Item

pytestmark = pytest.mark.django_db


def page_of(response) -> str:
    """The page as text.

    Args:
        response: The response.

    Returns:
        Its content.
    """
    assert response.status_code == 200
    return response.content.decode()


def row(page: str, login: str) -> str:
    """The row of a person in the table of replies.

    Args:
        page: The page.
        login: The handle of the person.

    Returns:
        The HTML of the row.
    """
    start = page.index(f'/people/{login}/"')
    return page[page.rindex("<tr", 0, start) : page.index("</tr>", start)]


def test_the_columns_of_the_page(replied, signed_in):
    """The titles of the columns."""
    page = page_of(signed_in.get(f"/s/{replied['project'].pk}/replies/"))
    table = page[page.index('id="replies-table"') :]
    titles = re.findall(r"<th[^>]*>([^<]+)</th>", table[: table.index("</thead>")])
    assert titles == [
        "Badge",
        "Person",
        "PRs replied to",
        "PRs merged",
        "Not replied to and open",
        "Not replied to and closed",
        "PRs closed by others",
        "Links",
    ]


def test_the_page_lists_open_pull_requests_without_reply_first(replied, signed_in):
    """bob and cid have an open one without reply; then the smallest share of answers."""
    page = page_of(signed_in.get(f"/s/{replied['project'].pk}/replies/"))
    assert re.findall(r'data-status="(\w+)"', page) == [
        "yellow",
        "red",
        "yellow",
        "green",
        "green",
        "green",
    ]
    assert "3 answered everything, 2 did not answer their only pull request, 1 did not" in page


def test_who_did_not_answer_has_the_details(replied, signed_in):
    """cid: one of two without reply, linked on GitHub, grouped by the repository."""
    page = page_of(signed_in.get(f"/s/{replied['project'].pk}/replies/"))
    cid = row(page, "cid")
    assert 'href="https://github.com/o/r/pull/4">#4</a>' in cid
    assert "o/r" in cid and "1/2" in cid
    cells = re.findall(r"<td>(.*?)</td>", cid, re.S)
    assert "#4" in cells[1] and cells[2].strip() == "-", "#4 is open: not in the closed column"
    assert 'href="https://github.com/cid"' not in cid, "no link to the profile"
    assert f"/s/{replied['project'].pk}/people/cid/items/?kind=pr" in cid
    ben = re.sub(r"<[^>]+>", " ", row(page, "ben"))
    assert re.search(r"0/1\s+0/1\s+-\s+o/r\s+#3\s+1", ben), "#3 closed without reply, by maint"


def test_who_answered_has_no_details(replied, signed_in):
    """ann answered everything: no list, no closed ones; the links stay."""
    ann = row(page_of(signed_in.get(f"/s/{replied['project'].pk}/replies/")), "ann")
    assert "pull/" not in ann
    assert ann.count(">-</td>") == 3
    assert "/people/ann/items/?kind=pr" in ann and "answered" in ann
    assert re.search(r"2/2</td>\s*<td[^>]*>1/3</td>", ann), "2 of 2 replied to, 1 of 3 merged"


def test_the_page_is_in_the_navigation(replied, signed_in):
    """The other pages link to the page of replies, with the time range."""
    page = page_of(signed_in.get(f"/s/{replied['project'].pk}/?last=30"))
    assert f'href="/s/{replied["project"].pk}/replies/?last=30"' in page


def test_visitors_see_public_repositories(replied, client):
    """o~r is public: no sign in."""
    page = page_of(client.get("/s/o~r/replies/"))
    assert 'data-status="red"' in page


def test_projects_need_a_sign_in(replied, client):
    """A project is shown to its owner only."""
    response = client.get(f"/s/{replied['project'].pk}/replies/")
    assert response.status_code == 302 and "/accounts/login/" in response["Location"]


def test_commits_not_read_are_named(replied, signed_in):
    """A pull request read before commits were read is counted on the page."""
    page = page_of(signed_in.get(f"/s/{replied['project'].pk}/replies/"))
    assert "1 pull request was read before commits were read" in page


def test_nobody_with_feedback(user, signed_in, world):
    """A page without pull requests with feedback says so."""
    Item.objects.filter(kind=Item.PR).delete()
    page = page_of(signed_in.get(f"/s/{world['project'].pk}/replies/"))
    assert "Nobody got feedback on a pull request in this time." in page


def test_the_items_of_one_person(replied, signed_in):
    """The pull requests, issues or both of bob, not of Bobby."""
    pk = replied["project"].pk
    both = page_of(signed_in.get(f"/s/{pk}/people/ann/items/"))
    assert "/pull/1" in both and "/issues/1" in both
    prs = page_of(signed_in.get(f"/s/{pk}/people/ann/items/?kind=pr"))
    assert "/pull/1" in prs and "/issues/1" not in prs
    issues = page_of(signed_in.get(f"/s/{pk}/people/ann/items/?kind=issue"))
    assert "/pull/" not in issues and "/issues/1" in issues
    bob = page_of(signed_in.get(f"/s/{pk}/people/bob/items/"))
    assert "/pull/12" in bob and "/pull/11" not in bob
    assert 'name="author"' not in bob, "the person is chosen by the page"


def test_the_badge_page_has_the_code_to_copy(replied, signed_in):
    """The badge of a project has its secret token and links the page of replies."""
    project = replied["project"]
    page = page_of(signed_in.get(f"/s/{project.pk}/replies/cid/badge/"))
    image = f"http://testserver/badge/{project.badge_token}/replies/cid.svg"
    assert f'data-share-image="{image}"' in page
    assert 'data-share-link="http://testserver/s/o~r/replies/cid/' in page, "to the replies of cid"
    assert f'href="/s/{project.pk}/replies/cid/">cid</a>' in page, "the path names the person"
    assert "js/share.js" in page


def test_the_badge_page_of_public_repositories(replied, client):
    """Visitors get the public address of the badge."""
    page = page_of(client.get("/s/o~r/replies/ben/badge/"))
    assert 'data-share-image="http://testserver/badge/s/o~r/replies/ben.svg"' in page


@pytest.mark.parametrize(
    ("login", "color", "text"),
    [
        ("ann", "#2da44e", "0/2 PRs unanswered"),
        ("ben", "#bf8700", "1/1 PRs unanswered"),
        ("cid", "#cf222e", "1/2 PRs unanswered"),
        ("dot", "#9f9f9f", "no feedback yet"),
        ("nobody", "#9f9f9f", "no feedback yet"),
    ],
)
def test_the_colours_of_the_badges(replied, client, login, color, text):
    """Green, yellow, red, or grey without feedback; for everybody."""
    response = client.get(f"/badge/s/o~r/replies/{login}.svg")
    assert response["Content-Type"] == "image/svg+xml"
    svg = response.content.decode()
    assert color in svg and f"<title>{login}: {text}</title>" in svg


def test_the_badge_of_a_project(replied, client):
    """The secret token counts with the classes of the owner; a wrong one is not found."""
    token = replied["project"].badge_token
    assert "#cf222e" in client.get(f"/badge/{token}/replies/cid.svg").content.decode()
    assert client.get("/badge/wrong/replies/cid.svg").status_code == 404
    assert client.get(f"/badge/s/{replied['project'].pk}/replies/cid.svg").status_code == 404
    assert client.get("/badge/s/unknown~repo/replies/cid.svg").status_code == 404


def test_several_projects_share_their_public_repositories(replied, signed_in):
    """Two projects together have no secret token: the badge counts their public repositories."""
    from ..factories import ProjectFactory

    other = ProjectFactory(user=replied["user"], target="o", repositories=[replied["repository"]])
    scope = f"{replied['project'].pk}-{other.pk}"
    page = page_of(signed_in.get(f"/s/{scope}/replies/cid/badge/"))
    assert 'data-share-image="http://testserver/badge/s/o~r/replies/cid.svg"' in page
    replied["repository"].is_private = True
    replied["repository"].save()
    page = page_of(signed_in.get(f"/s/{scope}/replies/cid/badge/"))
    assert "These projects together have no public repository and no badge" in page
    assert "data-share-image" not in page


def test_the_person_page_links_their_pull_requests_and_issues(replied, client):
    """The counts at the top lead to the lists, with the time range of the page."""
    page = page_of(client.get("/s/o~r/people/ann/?since=2026-01-01"))
    assert 'href="/s/o~r/people/ann/items/?kind=pr&amp;since=2026-01-01"' in page
    assert 'href="/s/o~r/people/ann/items/?kind=issue&amp;since=2026-01-01"' in page
    issues = page_of(client.get("/s/o~r/people/ann/items/?kind=issue&since=2026-01-01"))
    assert "/issues/1" in issues and "/pull/" not in issues


def test_the_badge_page_names_the_person(replied, client):
    """The handle is the address; the name of the GitHub profile is shown next to it."""
    from community_insights.models import Person

    Person.objects.update_or_create(login="ben", defaults={"name": "Ben Example"})
    page = page_of(client.get("/s/o~r/replies/ben/badge/"))
    assert "Badge of ben" in page and "Ben Example" in page


def test_the_replies_of_one_person(replied, client):
    """cid's pull requests: the open one without reply first, with their titles."""
    page = page_of(client.get("/s/o~r/replies/cid/"))
    table = page[page.index('id="pulls-table"') :]
    assert re.findall(r'data-replied="(\w+)"', table) == ["no", "yes", "none"]
    assert table.index("o/r#4") < table.index("o/r#6") < table.index("o/r#5")
    assert "Item 4" in table, "the title"
    assert "1 of 2 pull requests with feedback were replied to; 0 merged." in page
    assert 'href="/s/o~r/replies/cid/badge/"' in page, "the badge leads to its code"
    assert '<img src="/badge/s/o~r/replies/cid.svg"' in page
    assert ">Update</button>" in page


def test_merged_and_closed_pull_requests_of_a_person(replied, client):
    """ann's merged PR 13 needs no reply; ben's PR 3 was closed by maint."""
    ann = page_of(client.get("/s/o~r/replies/ann/"))
    assert "merged: needs no reply" in ann and "1 merged." in ann
    ben = page_of(client.get("/s/o~r/replies/ben/"))
    assert "closed by maint" in ben


def test_the_path_of_the_replies_of_a_person(replied, client):
    """The project, Replies and the person, each linked but the page itself."""
    page = page_of(client.get("/s/o~r/replies/ben/"))
    path = page[page.index('class="breadcrumb"') : page.index("</ol>")]
    assert 'href="/s/o~r/"' in path and 'href="/s/o~r/replies/"' in path
    assert 'aria-current="page">ben</li>' in path


def test_a_person_without_pull_requests(replied, client):
    """Somebody without pull requests gets an empty table, not an error."""
    page = page_of(client.get("/s/o~r/replies/nobody/"))
    assert "No pull requests in this time." in page


def test_the_list_leads_to_the_replies_of_each_person(replied, signed_in):
    """The label of a row opens the replies of the person."""
    page = page_of(signed_in.get(f"/s/{replied['project'].pk}/replies/"))
    assert f'href="/s/{replied["project"].pk}/replies/cid/"' in row(page, "cid")


def test_a_pull_request_the_author_closed_is_named_on_the_page_of_the_person(replied, client):
    """fay's PR 10 is shown, but marked as not counted."""
    page = page_of(client.get("/s/o~r/replies/fay/"))
    assert 'data-replied="given-up"' in page
    assert "closed by the author: not counted" in page


def test_how_many_contributors_are_shown(replied, signed_in):
    """Of the 10 people with a pull request (not the bot), 6 have one that counts; a link
    says why: dot, eve, fay and gil have no feedback to reply to."""
    page = page_of(signed_in.get(f"/s/{replied['project'].pk}/replies/"))
    assert "6/10 contributors shown." in page
    assert "reference/replies.html#which-pull-requests-count" in page
    assert "Why not all are shown" in page


def logins(page: str) -> list[str]:
    """The people of the table of replies, in their order.

    Args:
        page: The page.

    Returns:
        Their handles.
    """
    table = page[page.index('id="replies-table"') :]
    return re.findall(r'/people/([^/]+)/"', table)


def test_the_order_of_the_table_can_be_chosen(replied, client):
    """order names the keys, the first counts most; the arrows move a key."""
    by_default = logins(page_of(client.get("/s/o~r/replies/")))
    assert by_default[:2] == ["bob", "cid"], "an open pull request without reply first"
    by_person = logins(page_of(client.get("/s/o~r/replies/?order=person")))
    assert by_person == sorted(by_default, key=str.lower)
    dragged = logins(page_of(client.get("/s/o~r/replies/?order=badge&order=person")))
    assert dragged[0] == "cid", "red first, as Sortable.js sends one field per key"
    assert logins(page_of(client.get("/s/o~r/replies/?order=nonsense"))) == by_default


def test_the_order_field_moves_keys_with_arrows(replied, client):
    """Each key links the order with it one place earlier and later, keeping the range."""
    page = page_of(client.get("/s/o~r/replies/?last=30&order=person"))
    assert 'data-sort-list data-sort-form="reply-order"' in page
    assert (
        'href="/s/o~r/replies/?last=30&amp;order=open+person+replied+badge+closed+merged"' in page
    )
    assert "js/sortable-order.js" in page and "vendor/sortable/Sortable.min.js" in page


def test_visitors_learn_which_tokens_update_a_public_badge(replied, client):
    """Not signed in: the shared tokens, and a sign in to add one's own."""
    page = page_of(client.get("/s/o~r/replies/cid/badge/"))
    assert "The tokens shared on this site for everybody update the badge" in page
    assert 'href="/accounts/login/?next=/s/o~r/replies/cid/badge/">Sign in</a>' in page
    assert 'name="which"' not in page


def test_allow_a_token_for_a_badge_on_its_page(replied, signed_in):
    """Signed in: one of my tokens for this badge, or for all badges of the scope."""
    from community_insights.models import TokenGrant

    from ..factories import AccessTokenFactory

    token = AccessTokenFactory(user=replied["user"], label="mine", shared_percent=0)
    url = "/s/o~r/replies/cid/badge/"
    signed_in.post(url, {"id": token.pk, "which": "badge", "percent": "20"})
    signed_in.post(url, {"id": token.pk, "which": "all", "percent": "5"})
    grants = TokenGrant.objects.filter(token=token).order_by("login")
    assert list(grants.values_list("kind", "scope", "login", "percent")) == [
        ("badges", "o~r", "", 5),
        ("badges", "o~r", "cid", 20),
    ]
    page = page_of(signed_in.get(url))
    assert "Your tokens update it, too:" in page
    assert "mine: all badges of o/r" in page and "mine: the badge of cid" in page
    other = page_of(signed_in.get("/s/o~r/replies/ben/badge/"))
    assert "mine: all badges of o/r" in other and "the badge of cid" not in other


def test_only_own_tokens_can_be_allowed(replied, signed_in):
    """The token of somebody else is not found."""
    from ..factories import AccessTokenFactory

    theirs = AccessTokenFactory(shared_percent=0)
    response = signed_in.post("/s/o~r/replies/cid/badge/", {"id": theirs.pk, "which": "all"})
    assert response.status_code == 404
    assert not theirs.grants.exists()


@pytest.mark.parametrize(
    ("extension", "content_type", "start"),
    [
        ("svg", "image/svg+xml", b"<?xml"),
        ("png", "image/png", b"\x89PNG"),
        ("json", "application/json", b"{"),
    ],
)
def test_a_reply_badge_in_each_format(replied, client, extension, content_type, start):
    """badge.svg, badge.png and badge.json, kept for an hour."""
    response = client.get(f"/badge/s/o~r/replies/cid.{extension}")
    assert response["Content-Type"] == content_type
    assert response.content.startswith(start)
    assert response["Cache-Control"] == "public, max-age=3600"


def test_the_json_of_a_reply_badge_has_the_row_of_the_table(replied, client):
    """The spec of the badge for shields.io and the numbers of the table."""
    response = client.get("/badge/s/o~r/replies/cid.json")
    assert response["Access-Control-Allow-Origin"] == "*"
    assert response.json() == {
        "schemaVersion": 1,
        "label": "cid",
        "message": "1/2 PRs unanswered",
        "color": "#cf222e",
        "login": "cid",
        "page": "http://testserver/s/o~r/replies/cid/",
        "status": "red",
        "pull_requests": 3,
        "merged": 0,
        "counted": 3,
        "with_feedback": 2,
        "replied": 1,
        "not_replied": 1,
        "not_replied_open": {"o/r": [4]},
        "not_replied_closed": {},
        "closed_by_others": 0,
    }
    nobody = client.get("/badge/s/o~r/replies/nobody.json").json()
    assert (nobody["message"], nobody["status"]) == ("no feedback yet", None)


def test_the_json_of_a_project_badge(replied, client):
    """The secret badge has a JSON too, without a public page."""
    token = replied["project"].badge_token
    found = client.get(f"/badge/{token}/replies/ben.json").json()
    assert (found["status"], found["page"]) == ("yellow", None)


def test_unknown_formats_of_badges(replied, client):
    """Only svg, png and json."""
    assert client.get("/badge/s/o~r/replies/cid.gif").status_code == 404


def test_the_badge_page_switches_formats_and_links_the_json(replied, client):
    """SVG by default; PNG on choice; the JSON is linked."""
    page = page_of(client.get("/s/o~r/replies/cid/badge/"))
    assert '<img src="/badge/s/o~r/replies/cid.svg"' in page
    assert 'href="http://testserver/badge/s/o~r/replies/cid.json"' in page
    assert 'href="?format=png"' in page
    png = page_of(client.get("/s/o~r/replies/cid/badge/?format=png"))
    assert '<img src="/badge/s/o~r/replies/cid.png"' in png
    assert 'data-share-image="http://testserver/badge/s/o~r/replies/cid.png"' in png
