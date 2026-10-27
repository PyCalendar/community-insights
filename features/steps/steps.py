from behave import given, then, when
from selenium.common.exceptions import (
    ElementNotInteractableException,
    StaleElementReferenceException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait

from tests.fakes import item, node, repo

PASSWORD = "a long password 123"


def browser(context):
    """The browser.

    The first visit tells the site the time zone of the browser (django-tz-detect); the pages
    after it show it in the footer. That happens before a step uses a page.
    """
    if not context.time_zone_set:
        context.time_zone_set = True

        def known(driver):
            driver.get(context.get_url("/about/"))
            shown = driver.find_element(By.CSS_SELECTOR, "[data-time-zone]")
            return shown.get_attribute("data-time-zone") == context.timezone

        WebDriverWait(context.browser, 15, poll_frequency=0.5).until(known)
    return context.browser


def wait_for(context, condition, timeout=10):
    """Wait until the condition is true, or fail after `timeout` seconds.

    A page that is replaced while the condition looks at it (after a form is sent) is looked
    at again.
    """
    return WebDriverWait(
        context.browser, timeout, ignored_exceptions=[StaleElementReferenceException]
    ).until(lambda driver: condition())


def submit_form_with(context, field_name, value):
    """Fill a field and send its form."""
    field = browser(context).find_element(By.NAME, field_name)
    field.clear()
    field.send_keys(value)
    field.find_element(By.XPATH, "./ancestor::form").submit()


def click_button(context, text):
    """Click the button or link with the text, scrolled into view."""
    button = browser(context).find_element(
        By.XPATH, f"//button[normalize-space()='{text}'] | //a[normalize-space()='{text}']"
    )
    browser(context).execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
    button.click()


def open_menu(context):
    """Open the menu on a phone.

    On a phone the navigation is collapsed behind the toggler: open it and wait until Bootstrap
    has finished sliding it open.
    """

    def opened():
        try:
            toggler = browser(context).find_elements(By.CSS_SELECTOR, ".navbar-toggler")
            if not toggler or not toggler[0].is_displayed():
                return True  # wide screen: the menu is always shown
            if toggler[0].get_attribute("aria-expanded") != "true":
                toggler[0].click()
            classes = browser(context).find_element(By.ID, "menu").get_attribute("class")
            return "show" in classes and "collapsing" not in classes
        except StaleElementReferenceException:
            return False

    wait_for(context, opened)


@given('I open "{path}"')
@when('I open "{path}"')
def open_path(context, path):
    """Open an address of the site."""
    browser(context).get(context.get_url(path))


@then('I see "{text}"')
def see(context, text):
    """The text is on the page."""
    wait_for(context, lambda: text in browser(context).find_element(By.TAG_NAME, "body").text)


@then('I do not see "{text}"')
def do_not_see(context, text):
    """The text is not on the page."""
    assert text not in browser(context).find_element(By.TAG_NAME, "body").text, text


@then('the title is "{title}"')
def title_is(context, title):
    """The page has this title."""
    assert browser(context).title == title, browser(context).title


@then('the footer links to "{text}"')
def footer_links(context, text):
    """The footer has a link with the text."""
    links = browser(context).find_elements(By.CSS_SELECTOR, "footer a")
    assert any(link.text == text for link in links), [link.text for link in links]


@then('the link "{text}" goes to "{start}"')
def link_goes_to(context, text, start):
    """The link with the text goes to an address that starts like that."""
    link = browser(context).find_element(By.LINK_TEXT, text)
    assert link.get_attribute("href").startswith(start), link.get_attribute("href")


@when('I click "{text}"')
def click(context, text):
    """Click the button or link with the text."""
    click_button(context, text)


@when('I click "{text}" in the menu')
def click_in_menu(context, text):
    """Click a link of the menu, opening it first on a phone."""
    open_menu(context)

    def clicked():
        # The menu slides open: the link can be replaced or hidden for a moment.
        try:
            link = browser(context).find_element(
                By.XPATH, f"//*[@id='menu']//a[normalize-space()='{text}']"
            )
            if not link.is_displayed():
                return False
            # a click while the menu slides open can miss: click in the page
            browser(context).execute_script("arguments[0].click();", link)
            return True
        except (StaleElementReferenceException, ElementNotInteractableException):
            return False

    wait_for(context, clicked)


@given('I signed up as "{email}"')
def sign_up(context, email):
    """Sign up with the email address and a password."""
    browser(context).get(context.get_url("/accounts/signup/"))
    browser(context).find_element(By.NAME, "email").send_keys(email)
    browser(context).find_element(By.NAME, "password1").send_keys(PASSWORD)
    browser(context).find_element(By.NAME, "password2").send_keys(PASSWORD)
    browser(context).find_element(By.NAME, "password2").submit()
    wait_for(context, lambda: "/dashboard/" in browser(context).current_url)


@given("I added a GitHub token")
@when("I add a GitHub token")
def add_token(context):
    """Add a GitHub token on the page GitHub access."""
    browser(context).get(context.get_url("/dashboard/github/"))
    submit_form_with(context, "token", "github_pat_test")
    see(context, "The token of alice was saved.")


@given('GitHub has the repository "{name}" with {stars:d} stars')
def github_has_repository(context, name, stars):
    """The fake GitHub has a repository, also suggested to the user."""
    context.fake.listed.append(repo(name, stars))
    context.fake.suggested.append({"name": name, "kind": "yours", "stars": stars})


@given('the token cannot read "{name}"')
def token_cannot_read(context, name):
    """The fake token cannot see the repository."""
    context.fake.hidden.add(name)


@given("the repository has pull requests and issues")
def repository_has_items(context):
    """The fake repository has pull requests, issues, comments and reviews."""
    context.fake.prs = [
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
    context.fake.issues = [
        item(1, "bob", "2026-01-05T23:30:00Z", comments=[node("dave", "2026-01-07T10:00:00Z")]),
    ]
    context.fake.known = {
        "bob": {"login": "bob", "name": "Bob", "location": "Berlin", "avatarUrl": ""}
    }


def pick_source(context, text, entry):
    """Type into the source picker and choose an entry."""
    field = browser(context).find_element(By.CSS_SELECTOR, "[data-sources=input]")
    browser(context).execute_script("arguments[0].scrollIntoView({block: 'center'});", field)
    field.clear()
    field.send_keys(text)

    def buttons():
        return browser(context).find_elements(By.CSS_SELECTOR, "[data-sources=list] button")

    wait_for(context, lambda: any(b.text.startswith(entry) for b in buttons()))
    next(b for b in buttons() if b.text.startswith(entry)).click()


def open_dashboard_tab(context, name):
    """Open the dashboard and one of its tabs."""
    browser(context).get(context.get_url("/dashboard/"))
    click_button(context, name)
    wait_for(context, lambda: browser(context).find_element(By.ID, "pane-mine").is_displayed())


@when('I add the project "{target}"')
@given('I added the project "{target}"')
def add_project(context, target):
    """Add a repository with the source picker."""
    open_dashboard_tab(context, "Add repositories")
    pick_source(context, target, f"Add {target}")
    see(context, f"{target} was added.")


@when('I choose "{name}" from my repositories')
def choose_mine(context, name):
    """Add one of the suggested repositories."""
    open_dashboard_tab(context, "Add repositories")
    pick_source(context, name.split("/")[0], name)
    see(context, f"{name} was added.")


@given('I read the project "{target}" from GitHub')
@when('I read the project "{target}" from GitHub')
def read_project(context, target):
    """Read a project from GitHub: estimate, confirm, and wait for the data."""
    browser(context).get(context.get_url("/dashboard/"))
    browser(context).find_element(By.LINK_TEXT, target).click()
    click_button(context, "Read from GitHub")
    see(context, "API points")
    browser(context).find_element(By.CSS_SELECTOR, "form.card button.btn-primary").click()
    see(context, "100% of the data")


def show_all_images(context):
    """Images load lazily when they come into view: scroll to each of them."""
    browser(context).execute_script(
        "document.querySelectorAll('img').forEach(i => i.scrollIntoView({block: 'center'}))"
    )


@then("all images are loaded")
def images_loaded(context):
    """All images of the page are loaded."""
    show_all_images(context)

    def loaded():
        return browser(context).execute_script(
            "return Array.from(document.images).filter(i => i.src)"
            ".every(i => i.complete && i.naturalWidth > 0)"
        )

    wait_for(context, loaded)


@when('I choose "{value}" as the badge {part}')
def choose_badge(context, value, part):
    """Choose a value of the badge builder."""
    select = browser(context).find_element(By.CSS_SELECTOR, f'[data-badge="{part}"]')
    browser(context).execute_script("arguments[0].scrollIntoView({block: 'center'});", select)
    Select(select).select_by_visible_text(value)


@then('the badge markdown contains "{text}"')
def badge_markdown(context, text):
    """The Markdown of the badge contains the text."""

    def found():
        value = browser(context).find_element(By.CSS_SELECTOR, '[data-share="markdown"]')
        return text in value.get_attribute("value")

    wait_for(context, found)


@then("the badge preview is shown")
def badge_preview(context):
    """The badge preview is loaded."""
    wait_for(
        context,
        lambda: browser(context).execute_script(
            "const i = document.querySelector('[data-badge=preview]');"
            "return i.complete && i.naturalWidth > 0"
        ),
    )


@then("the site shows times in the time zone of the browser")
def time_zone_known(context):
    """The footer shows the time zone of the browser."""
    shown = browser(context).find_element(By.CSS_SELECTOR, "[data-time-zone]")
    assert shown.get_attribute("data-time-zone") == context.timezone


@then("I see the time zone of the browser")
def see_timezone(context):
    """The time zone of the browser is on the page."""
    see(context, context.timezone)


@then("the page does not scroll sideways")
def no_horizontal_scroll(context):
    """The page is not wider than the window."""
    width = browser(context).execute_script(
        "return [document.documentElement.scrollWidth, document.documentElement.clientWidth]"
    )
    assert width[0] <= width[1] + 1, width


@then("there are no errors in the page")
def no_errors(context):
    """The page shows no server error."""
    assert "Server Error" not in browser(context).page_source


@when("I choose the {theme} theme")
def choose_theme(context, theme):
    """Choose light, dark or auto with the switch of the menu."""
    open_menu(context)
    button = browser(context).find_element(By.CSS_SELECTOR, f'[data-theme-set="{theme}"]')
    browser(context).execute_script("arguments[0].click();", button)


@then("the page is {theme}")
def page_theme(context, theme):
    """The page is shown in that theme."""
    wait_for(
        context,
        lambda: (
            browser(context).execute_script(
                "return document.documentElement.getAttribute('data-theme')"
            )
            == theme
        ),
    )


@then("the charts are {theme}")
def charts_theme(context, theme):
    """All charts are drawn in that theme."""
    show_all_images(context)

    def switched():
        sources = browser(context).execute_script(
            "return Array.from(document.querySelectorAll('img[data-chart-src]'))"
            ".map(i => i.complete && i.naturalWidth > 0 ? i.src : '')"
        )
        return sources and all(f"theme={theme}" in source for source in sources)

    wait_for(context, switched)


def query_field(context):
    """The field of the query on the contributors page."""
    return browser(context).find_element(By.ID, "where")


@when('I type "{text}" into the query')
def type_query(context, text):
    """Type at the end of the query."""
    field = query_field(context)
    browser(context).execute_script("arguments[0].scrollIntoView({block: 'center'});", field)
    field.send_keys(text)


@when("I press {key} in the query")
def press_in_query(context, key):
    """Press Enter, Tab, ArrowDown or Escape in the query field."""
    keys = {"Enter": Keys.ENTER, "Tab": Keys.TAB, "ArrowDown": Keys.ARROW_DOWN}
    query_field(context).send_keys(keys[key])


@then('the query suggests "{name}"')
def query_suggests(context, name):
    """The list of names under the query shows the name."""

    def shown():
        lists = browser(context).find_elements(By.CSS_SELECTOR, ".complete-list")
        return lists and lists[0].is_displayed() and name in lists[0].text.split()

    wait_for(context, shown)


@then('the query is "{text}"')
def query_is(context, text):
    """The text of the query field; a space at the end counts."""
    wait_for(context, lambda: query_field(context).get_attribute("value") == text)


@then('the address has the query "{text}"')
def address_has_query(context, text):
    """The query was run: the address of the page has it."""
    from urllib.parse import parse_qs, urlsplit

    def sent():
        parameters = parse_qs(urlsplit(browser(context).current_url).query)
        return parameters.get("where", [""])[0].strip() == text

    wait_for(context, sent)


def column_button(context, name, label):
    """A button of a column of the column editor."""
    chip = browser(context).find_element(By.CSS_SELECTOR, f'.column-chip[data-column="{name}"]')
    browser(context).execute_script("arguments[0].scrollIntoView({block: 'center'});", chip)
    found = (
        f'[aria-label="{label} {name}"]'
        if label == "Remove"
        else f'[aria-label="{label} {name} left"]'
    )
    return chip.find_element(By.CSS_SELECTOR, found)


@when('I remove the column "{name}"')
def remove_column(context, name):
    """Remove a column with its button."""
    column_button(context, name, "Remove").click()


@when('I move the column "{name}" left')
def move_column_left(context, name):
    """Move a column one place to the left with its button."""
    column_button(context, name, "Move").click()


@when('I add the column "{name}"')
def add_column(context, name):
    """Add a column with the select under the columns."""
    select = browser(context).find_element(By.CSS_SELECTOR, ".column-list + select")
    browser(context).execute_script("arguments[0].scrollIntoView({block: 'center'});", select)
    Select(select).select_by_visible_text(name)


@then('the table has the columns "{names}" first')
def table_columns(context, names):
    """The first columns of the table of the contributors."""
    wanted = names.split()

    def shown():
        heads = browser(context).find_elements(
            By.CSS_SELECTOR, "table.align-middle thead th .name-variable"
        )
        return [h.text for h in heads][: len(wanted)] == wanted

    wait_for(context, shown)


@then('the table has no column "{name}"')
def table_has_no_column(context, name):
    """The table of the contributors does not show the column."""
    heads = browser(context).find_elements(
        By.CSS_SELECTOR, "table.align-middle thead th .name-variable"
    )
    assert name not in [h.text for h in heads], [h.text for h in heads]


@then('the code to share in {name} contains "{text}"')
def share_code(context, name, text):
    """The field of a format of the share page has the text."""
    formats = {"Markdown": "markdown", "reStructuredText": "rst", "HTML": "html", "Link": "link"}
    field = browser(context).find_element(By.CSS_SELECTOR, f'[data-share="{formats[name]}"]')
    wait_for(context, lambda: text in field.get_attribute("value"))


@then('the theme switch shows "{icon}"')
def theme_icon(context, icon):
    """The button of the theme switch shows the icon of the choice."""
    wait_for(
        context,
        lambda: (
            browser(context)
            .find_element(By.CSS_SELECTOR, "[data-theme-icon]")
            .get_attribute("textContent")
            == icon
        ),
    )
