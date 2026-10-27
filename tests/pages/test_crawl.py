"""Every page and every link works."""

from html.parser import HTMLParser
from urllib.parse import urldefrag, urljoin, urlparse

import pytest
from django.contrib.staticfiles import finders
from django.contrib.staticfiles.storage import staticfiles_storage

from ..fakes import FakeClient

pytestmark = pytest.mark.django_db


SKIP = ("/accounts/logout", "/accounts/github/", "/admin/", "/accounts/3rdparty/")


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.resources, self.ids, self.anchors = [], [], set(), []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
        if tag in ("img", "script") and attrs.get("src"):
            self.resources.append(attrs["src"])
        if tag == "link" and attrs.get("href"):
            self.resources.append(attrs["href"])
        for name in ("data-bs-target", "aria-controls", "aria-labelledby", "for"):
            if attrs.get(name):
                self.anchors.append(attrs[name].lstrip("#"))


def static_exists(path: str) -> bool:
    name = path.removeprefix(staticfiles_storage.base_url).split("?")[0]
    return finders.find(name) is not None


def crawl(client, start: list[str], limit: int = 400) -> dict[str, int]:
    seen: dict[str, int] = {}
    todo = list(start)
    problems = []
    while todo and len(seen) < limit:
        url = todo.pop(0)
        if url in seen:
            continue
        response = client.get(url)
        seen[url] = response.status_code
        if response.status_code in (301, 302):
            todo.append(urldefrag(urljoin(url, response["Location"]))[0])
            continue
        if response.status_code != 200:
            problems.append(f"{url}: {response.status_code}")
            continue
        kind = response["Content-Type"]
        if url.endswith(".svg"):
            assert kind.startswith("image/svg+xml") and b"<svg" in response.content, url
            continue
        if not kind.startswith("text/html"):
            continue
        page = Links()
        page.feed(response.content.decode())
        for target in page.anchors:
            if target and target not in page.ids:
                problems.append(f"{url}: refers to #{target} which is not on the page")
        for resource in page.resources:
            parsed = urlparse(resource)
            if parsed.scheme in ("http", "https"):
                problems.append(f"{url}: loads {resource} from another server")
            elif resource.startswith(staticfiles_storage.base_url):
                if not static_exists(resource):
                    problems.append(f"{url}: missing static {resource}")
            else:
                todo.append(urljoin(url, resource))
        for link in page.links:
            parsed = urlparse(link)
            if parsed.scheme in ("http", "https", "mailto"):
                assert parsed.netloc or parsed.scheme == "mailto", f"{url}: {link}"
                continue
            target = urldefrag(urljoin(url, link))[0]
            if not target or target.startswith(SKIP):
                continue
            if target.startswith(staticfiles_storage.base_url):
                if not static_exists(target):
                    problems.append(f"{url}: missing static {target}")
                continue
            todo.append(target)
    assert not problems, "\n".join(problems)
    return seen


def test_every_page_and_link_works_signed_in(world, signed_in, monkeypatch):  # noqa: F811
    # the fetch page asks GitHub for an estimate: mocked
    monkeypatch.setattr("community_insights.github.Client", lambda token: FakeClient())
    seen = crawl(signed_in, ["/", "/dashboard/"])
    pages = {urlparse(u).path for u in seen}
    project = world["project"].pk
    for expected in [
        "/dashboard/",
        "/about/",
        "/dashboard/classes/",
        "/dashboard/cache/",
        "/dashboard/github/",
        "/dashboard/downloads/",
        f"/s/{project}/",
        f"/s/{project}/contributors/",
        f"/s/{project}/people/bob/",
        f"/s/{project}/fetch/",
        f"/s/{project}/data/responses.csv",
        f"/s/{project}/data/contributors.csv",
    ]:
        assert expected in pages, expected
    assert len(seen) > 20


def test_every_public_page_works(client, world, monkeypatch):  # noqa: F811
    # the fetch page asks GitHub for an estimate: mocked
    monkeypatch.setattr("community_insights.github.Client", lambda token: FakeClient())
    seen = crawl(client, ["/", "/about/", "/accounts/login/", "/accounts/signup/"])
    assert all(code in (200, 302) for code in seen.values())
    pages = {urlparse(u).path for u in seen}
    for expected in ["/explore/", "/s/o~r/", "/s/o~r/contributors/", "/s/o~r/items/"]:
        assert expected in pages, expected
    assert client.get(f"/s/{world['project'].pk}/").status_code == 302  # sign in first
