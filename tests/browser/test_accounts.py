"""Accounts and GitHub access: people sign up with an email address and add tokens."""


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
    items.nth(1).locator("[data-sort-handle]").drag_to(items.nth(0).locator("[data-sort-handle]"))
    alice.page.wait_for_load_state()
    assert (
        alice.page.locator("[data-sort-list] [data-sort-id]").nth(1).get_attribute("data-sort-id")
        == first
    )


def test_the_menu_works_on_any_screen(alice):
    """The menu opens on a phone, too."""
    alice.click_in_menu("Classes")
    alice.see("Classes of people")
