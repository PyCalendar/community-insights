"""Projects and their statistics."""

import re

from playwright.sync_api import expect


def test_read_a_project_and_see_its_numbers_and_charts(project):
    """After reading, the overview has its numbers and charts."""
    project.add_project("o/r")
    project.read_project("o/r")
    for text in ("Pull requests", "merged", "3 of 3 items"):
        project.see(text)
    project.images_are_loaded()
    project.does_not_scroll_sideways()


def test_the_charts_are_drawn_by_chart_js(read):
    """The charts with data become canvases of Chart.js; the SVG stays for those without."""
    read.see("Response times")
    canvas = read.page.locator(".chart-canvas canvas").first
    expect(canvas).to_be_visible()
    expect(canvas).to_have_attribute("role", "img")
    expect(read.page.locator('img[data-chart-src*="survival-pr"]')).to_be_visible()


def test_the_dashboard_shows_a_card_with_a_menu_for_each_project(read):
    """The card of the project shows its numbers."""
    read.open("/dashboard/")
    read.see("Open pull requests")
    read.see("100% of the data")


def test_every_statistics_page_shows_its_data_sources(project):
    """Data and sources lists the tables to download."""
    project.add_project("o/r")
    project.open("/dashboard/")
    project.page.get_by_role("link", name="o/r", exact=True).first.click()
    project.see("0% of the data")
    project.click("Data and sources")
    project.see("Data sources")
    project.see("response times: ODS, CSV, Parquet")


def test_the_downloads_page_shows_what_was_fetched_and_why(read):
    """The downloads page lists the finished fetch and its reason."""
    read.click_in_menu("Downloads")
    read.see("Finished")
    read.see("Statistics of o/r")


def test_build_a_badge(read):
    """The badge builder makes the Markdown and shows the badge."""
    for part, value in (("kind", "issues"), ("percentile", "50"), ("class", "bot")):
        read.page.locator(f'[data-badge="{part}"]').select_option(label=value)
    expect(read.page.locator('[data-share="markdown"]')).to_have_value(
        re.compile("kind=issue&percentile=50&class=bot")
    )
    read.page.wait_for_function(
        "() => { const i = document.querySelector('[data-badge=preview]');"
        " return i.complete && i.naturalWidth > 0; }"
    )


def test_contributors_and_their_times_in_my_time_zone(read):
    """The contributors table and a person, in the time zone of the browser."""
    read.click("Contributors")
    read.see("bob")
    read.see("Berlin")
    read.page.get_by_role("link", name="bob", exact=True).first.click()
    read.see(read.timezone)
    read.images_are_loaded()


def test_dark_and_light_pages_with_charts_in_the_same_colours(read):
    """The theme switches the page and its charts, also on the next page."""
    read.choose_theme("dark")
    read.page_is("dark")
    read.charts_are("dark")
    read.open("/dashboard/")
    read.page.get_by_role("link", name="o/r", exact=True).first.click()
    read.page_is("dark")
    read.charts_are("dark")
    read.choose_theme("light")
    read.page_is("light")
    read.charts_are("light")


def test_write_a_query_with_the_names_of_the_variables_and_run_it_with_enter(read):
    """The query field completes the names; Enter runs the query and scrolls it to the top."""
    read.click("Contributors")
    field = read.page.locator("#where")
    field.press_sequentially("prs_mer")
    expect(read.page.locator(".complete-list")).to_contain_text("prs_merged")
    field.press("Tab")
    expect(field).to_have_value("prs_merged ")
    field.press_sequentially(">= 0")
    field.press("Enter")
    read.address_has_query("prs_merged >= 0")
    read.see("people")
    read.page.wait_for_function(
        "() => Math.abs(document.querySelector('.query-form').getBoundingClientRect().top) < 2"
    )
    expect(field).to_be_in_viewport()


def test_choose_the_columns_of_the_contributors(read):
    """Remove, move and add columns, then run the query."""
    read.click("Contributors")
    read.column_button("user_location", "Remove").click()
    read.column_button("user_class", "Move").click()
    read.page.locator(".column-list + select").select_option(label="activity_total")
    read.click("Run the query")
    expect(read.page.locator("table.align-middle thead th .name-variable").first).to_have_text(
        "user_class"
    )
    assert read.table_columns()[:2] == ["user_class", "user_handle"]
    assert "user_location" not in read.table_columns()
    read.see("activity_total")


def test_share_a_chart_with_the_page_it_comes_from(read):
    """The share page has the code for Markdown and reStructuredText."""
    read.click("Share this chart")
    read.see("Share a chart")
    expect(read.page.locator('[data-share="markdown"]')).to_have_value(
        re.compile("chart/responses-pr.svg")
    )
    expect(read.page.locator('[data-share="rst"]')).to_have_value(re.compile(":target: http"))
    read.images_are_loaded()


def test_the_colours_of_the_page_are_chosen_from_a_menu_with_an_icon(site):
    """The switch shows the icon of the choice."""
    site.open("/about/")
    site.choose_theme("dark")
    expect(site.page.locator("[data-theme-icon]")).to_have_text("☾")
    site.choose_theme("auto")
    expect(site.page.locator("[data-theme-icon]")).to_have_text("◐")
