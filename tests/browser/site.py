"""What people do on the site, in Firefox with Playwright."""

import re
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import Page, expect

from tests.fakes import item, node, repo

PASSWORD = "a long password 123"


class Site:
    """The site in a browser: open pages, click, type, and check what is shown.

    Playwright waits for each element before it acts on it, and ``expect`` waits until the
    page shows what is expected, so no step needs to wait itself.

    Args:
        page: The page of Playwright.
        url: The address of the live server.
        fake: The fake GitHub that the views use (``tests/fakes/client.py``).
        timezone: The time zone of the browser.
    """

    def __init__(self, page: Page, url: str, fake, timezone: str):
        """Use the site in the page.

        Args:
            page: The page of Playwright.
            url: The address of the live server.
            fake: The fake GitHub that the views use.
            timezone: The time zone of the browser.
        """
        self.page, self.url, self.fake, self.timezone = page, url, fake, timezone
        self.time_zone_known = False

    # pages and texts

    def open(self, path: str) -> None:
        """Open an address of the site; the first one waits until the site knows the time zone.

        django-tz-detect sends the time zone of the browser with the first page; the pages
        after it show it in the footer.

        Args:
            path: The path, such as ``/about/``.
        """
        if not self.time_zone_known:
            self.time_zone_known = True
            for _ in range(30):
                self.page.goto(self.url + "/about/")
                shown = self.page.locator("[data-time-zone]").get_attribute("data-time-zone")
                if shown == self.timezone:
                    break
                self.page.wait_for_timeout(500)
        self.page.goto(self.url + path)

    def see(self, text: str) -> None:
        """The text is on the page.

        Args:
            text: The text.
        """
        expect(self.page.locator("body")).to_contain_text(text)

    def do_not_see(self, text: str) -> None:
        """The text is not on the page.

        Args:
            text: The text.
        """
        expect(self.page.locator("body")).not_to_contain_text(text)

    def click(self, text: str) -> None:
        """Click the button or link with the text.

        Args:
            text: The text of the button or link.
        """
        self.page.locator(
            f"xpath=//button[normalize-space()='{text}'] | //a[normalize-space()='{text}']"
        ).first.click()

    def open_menu(self) -> None:
        """Open the menu on a phone; on a wide screen it is always open."""
        toggler = self.page.locator(".navbar-toggler")
        if toggler.is_visible() and toggler.get_attribute("aria-expanded") != "true":
            toggler.click()
            expect(self.page.locator("#menu")).to_have_class(re.compile(r"(^|\s)show(\s|$)"))

    def click_in_menu(self, text: str) -> None:
        """Click a link of the menu, opening it first on a phone.

        Args:
            text: The text of the link.
        """
        self.open_menu()
        self.page.locator("#menu").get_by_role("link", name=text, exact=True).click()

    def does_not_scroll_sideways(self) -> None:
        """The page is not wider than the window."""
        scroll, client = self.page.evaluate(
            "[document.documentElement.scrollWidth, document.documentElement.clientWidth]"
        )
        assert scroll <= client + 1, (scroll, client)

    def images_are_loaded(self) -> None:
        """All shown images of the page are loaded, also those loaded when seen (lazy)."""
        self.page.evaluate(
            "document.querySelectorAll('img').forEach(i => i.scrollIntoView({block: 'center'}))"
        )
        self.page.wait_for_function(
            "Array.from(document.images).filter(i => i.src && !i.hidden)"
            ".every(i => i.complete && i.naturalWidth > 0)"
        )

    # accounts and GitHub

    def sign_up(self, email: str) -> None:
        """Sign up with the email address and a password.

        Args:
            email: The address.
        """
        self.open("/accounts/signup/")
        self.page.fill("[name=email]", email)
        self.page.fill("[name=password1]", PASSWORD)
        self.page.fill("[name=password2]", PASSWORD)
        self.page.locator("[name=password2]").press("Enter")
        self.page.wait_for_url(re.compile("/dashboard/"))

    def add_token(self) -> None:
        """Add a GitHub token on the page GitHub access."""
        self.open("/dashboard/github/")
        self.page.fill("[name=token]", "github_pat_test")
        self.page.locator("[name=token]").press("Enter")
        self.see("The token of alice was saved.")

    def github_has(self, name: str, stars: int) -> None:
        """The fake GitHub has a repository, also suggested to the user.

        Args:
            name: The repository as ``owner/name``.
            stars: Its stars.
        """
        self.fake.listed.append(repo(name, stars))
        self.fake.suggested.append({"name": name, "kind": "yours", "stars": stars})

    def repository_has_items(self) -> None:
        """The fake repository has pull requests, issues, comments and reviews."""
        self.fake.prs = [
            item(
                1,
                "bob",
                "2026-01-05T10:00:00Z",
                comments=[node("ci[bot]", "2026-01-05T10:10:00Z", typename="Bot")],
                reviews=[node("maint", "2026-01-05T12:00:00Z", "MEMBER", key="submittedAt")],
                state="CLOSED",
                merged=True,
                updated="2026-01-05T12:00:00Z",
            ),
            item(2, "carol", "2026-01-06T09:00:00Z", reviews=[]),
        ]
        self.fake.issues = [
            item(1, "bob", "2026-01-05T23:30:00Z", comments=[node("dave", "2026-01-07T10:00:00Z")]),
        ]
        self.fake.known = {
            "bob": {"login": "bob", "name": "Bob", "location": "Berlin", "avatarUrl": ""}
        }

    def pick_source(self, text: str, entry: str) -> None:
        """Type into the source picker of the dashboard and choose an entry.

        Args:
            text: What to type.
            entry: The start of the text of the entry to choose.
        """
        self.open("/dashboard/")
        self.click("Add repositories")
        expect(self.page.locator("#pane-mine")).to_be_visible()
        field = self.page.locator("[data-sources=input]")
        field.fill(text)
        self.page.locator("[data-sources=list] button", has_text=entry).first.click()

    def add_project(self, target: str) -> None:
        """Add a repository with the source picker.

        Args:
            target: The repository.
        """
        self.pick_source(target, f"Add {target}")
        self.see(f"{target} was added.")

    def read_project(self, target: str) -> None:
        """Read a project from GitHub: estimate, confirm, and wait for the data.

        Args:
            target: The repository.
        """
        self.open("/dashboard/")
        self.page.get_by_role("link", name=target, exact=True).first.click()
        self.click("Read from GitHub")
        self.see("API points")
        self.page.locator("form.card button.btn-primary").click()
        self.see("100% of the data")

    # themes

    def choose_theme(self, theme: str) -> None:
        """Choose light, dark or auto with the switch of the menu.

        Args:
            theme: ``light``, ``dark`` or ``auto``.
        """
        self.open_menu()
        self.page.locator(f'[data-theme-set="{theme}"]').dispatch_event("click")

    def page_is(self, theme: str) -> None:
        """The page is shown in the theme.

        Args:
            theme: ``light`` or ``dark``.
        """
        expect(self.page.locator("html")).to_have_attribute("data-theme", theme)

    def charts_are(self, theme: str) -> None:
        """All charts are in the theme: their SVG, and the canvases of Chart.js drawn with it.

        Args:
            theme: ``light`` or ``dark``.
        """
        self.page.wait_for_function(
            "theme => {"
            " const charts = Array.from(document.querySelectorAll('img[data-chart-src]'));"
            " const drawn = Array.from(document.querySelectorAll('.chart-canvas'));"
            " return charts.length && charts.every(i => i.src.includes('theme=' + theme))"
            " && drawn.every(d => d.getAttribute('data-chart-theme') === theme); }",
            arg=theme,
        )

    # the contributors page

    def address_has_query(self, text: str) -> None:
        """The query was run: the address of the page has it.

        Args:
            text: The query.
        """
        self.page.wait_for_function(
            "text => new URLSearchParams(location.search).get('where')?.trim() === text",
            arg=text,
        )
        assert parse_qs(urlsplit(self.page.url).query)["where"][0].strip() == text

    def column_button(self, name: str, label: str):
        """A button of a column of the column editor.

        Args:
            name: The column.
            label: ``Remove`` or ``Move``.

        Returns:
            The button.
        """
        chip = self.page.locator(f'.column-chip[data-column="{name}"]')
        wanted = f"{label} {name}" if label == "Remove" else f"{label} {name} left"
        return chip.locator(f'[aria-label="{wanted}"]')

    def table_columns(self) -> list[str]:
        """The names of the columns of the table of the contributors.

        Returns:
            The names, as variables.
        """
        return self.page.locator("table.align-middle thead th .name-variable").all_inner_texts()
