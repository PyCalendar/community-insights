"""Accounts and GitHub access: people sign up with an email address and add tokens."""

import re

from playwright.sync_api import expect


def test_somebody_new_is_asked_for_github_access(alice):
    """A new account is asked to link GitHub or to add a token."""
    alice.see("link your GitHub account or add a personal access token")


def test_a_token_gives_access_to_github_and_my_repositories(alice):
    """With a token, the own repositories can be added."""
    alice.github_has("alice/tool", 7)
    alice.add_token()
    alice.open("/dashboard/")
    alice.click("Add repositories")
    alice.click("Refresh from GitHub")
    alice.pick_source("alice", "alice/tool")
    alice.see("alice/tool was added.")
    alice.do_not_see("link your GitHub account")


def test_a_token_without_expiry_is_warned_about(alice):
    """A token that never expires is refused by some organisations."""
    alice.add_token()
    alice.see("organisations such as Plone refuse")


def test_test_a_token_on_my_projects(alice):
    """The test of a token names the repositories it cannot read."""
    alice.add_token()
    alice.github_has("o/r", 1)
    alice.github_has("o/secret", 1)
    alice.add_project("o/r")
    alice.add_project("o/secret")
    alice.fake.hidden.add("o/secret")
    alice.open("/dashboard/github/")
    alice.click("Test on my projects")
    alice.see("cannot read 1 of 2 repositories: o/secret")


def test_the_tokens_can_be_dragged_into_another_order(alice):
    """Sortable.js sends the new order of the tokens when one is dropped."""
    alice.add_token()
    alice.open("/dashboard/github/")
    alice.page.fill("[name=token]", "github_pat_second")
    alice.page.locator("[name=token]").press("Enter")
    alice.see("2. ")
    items = alice.page.locator("[data-sort-list] [data-sort-id]")
    first = items.nth(0).get_attribute("data-sort-id")
    size = alice.page.viewport_size
    # both tokens in view, also on a phone, where each is taller than half the window
    alice.page.set_viewport_size({"width": size["width"], "height": 2400})
    items.nth(1).locator("[data-sort-handle]").drag_to(items.nth(0).locator("[data-sort-handle]"))
    # the drop sends the order and the page is loaded again: wait until it shows it
    expect(alice.page.locator("[data-sort-list] [data-sort-id]").nth(1)).to_have_attribute(
        "data-sort-id", first
    )
    alice.page.set_viewport_size(size)


def test_the_menu_works_on_any_screen(alice):
    """The menu opens on a phone, too."""
    alice.click_in_menu("Classes")
    alice.see("Classes of people")


def test_the_account_menu_opens_and_signs_out(alice):
    """The account menu opens on any screen, leads to its pages and signs out."""
    alice.click_in_menu("Explore")
    expect(alice.page).to_have_url(re.compile(r"/explore/$"))
    alice.open_menu()
    alice.page.locator(".account-menu .dropdown-toggle").click()
    sign_out = alice.page.locator(".account-menu").get_by_role(
        "button", name="Sign out", exact=True
    )
    expect(sign_out).to_be_visible()
    alice.does_not_scroll_sideways()
    sign_out.click()
    # the page after the sign out has no account menu; only then is its menu opened
    expect(alice.page.locator(".account-menu")).to_have_count(0)
    alice.open_menu()
    expect(
        alice.page.locator("#menu").get_by_role("link", name="Sign in", exact=True)
    ).to_be_visible()
