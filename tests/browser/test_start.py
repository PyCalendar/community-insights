"""The start page: people who are not signed in learn what the site does and can sign up."""

from playwright.sync_api import expect


def test_the_start_page_offers_to_sign_up(site):
    """The title is the name of the site, and it offers to sign up."""
    site.open("/")
    expect(site.page).to_have_title("Contributor Community Insights")
    site.see("Sign up with email")
    site.does_not_scroll_sideways()


def test_the_footer_links_to_the_about_page_and_to_bug_reports(site):
    """About and Report a bug are in the footer."""
    site.open("/")
    footer = site.page.locator("footer")
    expect(footer.get_by_role("link", name="About", exact=True)).to_be_visible()
    report = footer.get_by_role("link", name="Report a bug", exact=True)
    assert report.get_attribute("href").startswith(
        "https://github.com/PyCalendar/community-insights/issues/new"
    )


def test_the_about_page_shows_the_version_and_the_licenses(site):
    """Version, Django and Bootstrap are on the About page."""
    site.open("/about/")
    for text in ("Version", "Django", "Bootstrap"):
        site.see(text)


def test_the_time_zone_of_the_browser_is_sent_to_the_server(site):
    """The footer shows the time zone of the browser."""
    site.open("/")
    expect(site.page.locator("[data-time-zone]")).to_have_attribute("data-time-zone", site.timezone)


def test_switch_the_language_in_the_footer(site):
    """German and back to English."""
    site.open("/")
    site.click("Deutsch")
    site.see("Noch kein Repository")
    site.click("English")
    site.see("No repository yet")
