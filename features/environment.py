"""Browser tests with Firefox, like open-web-calendar.

    uv run python manage.py behave                         # headless Firefox
    uv run python manage.py behave -D headless=false       # watch it
    uv run python manage.py behave -D window=375x812       # phone size
    uv run python manage.py behave -D timezone=America/New_York

GitHub is never used: the client of the views is replaced by a fake in this
process, which also runs the live server.
"""

import os

from selenium import webdriver
from selenium.webdriver.firefox.service import Service


def before_all(context):
    """Start Firefox in the time zone and window size asked for.

    Start Firefox (headless unless -D headless=false) in the time zone and window size asked
    for.
    """
    from django.conf import settings

    settings.FETCH_WORKER = "inline"  # "Read from GitHub" finishes before the page loads
    userdata = context.config.userdata
    context.timezone = userdata.get("timezone", "Asia/Tokyo")
    options = webdriver.FirefoxOptions()
    if userdata.get("headless", "true").lower() != "false":
        options.add_argument("-headless")
    service = Service(env={**os.environ, "TZ": context.timezone})
    context.browser = webdriver.Firefox(options=options, service=service)
    width, height = userdata.get("window", "1280x900").split("x")
    context.browser.set_window_size(int(width), int(height))
    context.browser.implicitly_wait(5)


def after_all(context):
    """Close Firefox."""
    context.browser.quit()


def before_scenario(context, scenario):
    """Replace GitHub by a fake and start without cookies."""
    import community_insights.github
    from tests.fakes import FakeClient

    context.fake = FakeClient()
    context.original_client = community_insights.github.Client
    community_insights.github.Client = lambda token: context.fake
    context.browser.delete_all_cookies()
    context.time_zone_set = False  # see browser() in steps.py


def after_scenario(context, scenario):
    """Put the real GitHub client back."""
    import community_insights.github

    community_insights.github.Client = context.original_client
