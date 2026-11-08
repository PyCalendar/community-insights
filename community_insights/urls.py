from django.conf import settings
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.templatetags.static import static
from django.urls import include, path
from django.views.generic import RedirectView
from django.views.i18n import JavaScriptCatalog
from health_check.views import HealthCheckView

from .views import (
    access,
    badges,
    cache,
    charts,
    classes,
    compare,
    contributors,
    dashboard,
    documents,
    explore,
    exports,
    fetch,
    items,
    pages,
    profile,
    replies,
    statistics,
    users,
)

# The admin is signed in to like the site (django-allauth), with its limit of
# failed attempts, instead of its own login page without one.
admin.site.login = login_required(admin.site.login)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("tz_detect/", include("tz_detect.urls")),
    path("i18n/", include("django.conf.urls.i18n")),  # set_language: the switch in the footer
    path("jsi18n/", JavaScriptCatalog.as_view(), name="javascript-catalog"),
    path(
        "health/",
        HealthCheckView.as_view(
            checks=["health_check.checks.Database", "health_check.checks.Cache"]
        ),
        name="health",
    ),
    # browsers ask for /favicon.ico on their own; the icon of pycal.org is a PNG
    path("favicon.ico", RedirectView.as_view(url=static("img/favicon.png"), permanent=True)),
    path("", pages.home, name="home"),
    path("about/", pages.about, name="about"),
    path("about/licenses/<str:name>/", pages.license_text, name="license"),
    path("explore/", explore.explore, name="explore"),
    path("explore/submit/", explore.submit, name="explore_submit"),
    path("dashboard/", dashboard.dashboard, name="dashboard"),
    path("dashboard/classes/", classes.classes, name="classes"),
    path("dashboard/cache/", cache.cache, name="cache"),
    path("dashboard/users/", users.users, name="users"),
    path("dashboard/github/", access.github_access, name="github_access"),
    path("dashboard/profile/", profile.profile, name="profile"),
    path("dashboard/downloads/", fetch.downloads, name="downloads"),
    path("projects/<int:pk>/delete/", dashboard.project_delete, name="project_delete"),
    path("projects/<int:pk>/rename/", dashboard.project_rename, name="project_rename"),
    path("s/<str:scope>/", statistics.overview, name="overview"),
    path("s/<str:scope>/response-times/", statistics.response_times, name="response_times"),
    path("s/<str:scope>/badges/", statistics.badges, name="badges"),
    path("s/<str:scope>/fetch/", fetch.fetch, name="fetch"),
    path("s/<str:scope>/progress.json", fetch.progress, name="progress"),
    path("s/<str:scope>/add/", fetch.add_source, name="add_source"),
    path("s/<str:scope>/contributors/", contributors.contributors, name="contributors"),
    path(
        "s/<str:scope>/contributors.<str:extension>",
        contributors.contributors_download,
        name="contributors_download",
    ),
    path("s/<str:scope>/items/", items.items, name="items"),
    path("s/<str:scope>/compare/", compare.compare, name="compare"),
    path("s/<str:scope>/people/<str:login>/", statistics.person, name="person"),
    path("s/<str:scope>/people/<str:login>/items/", replies.person_items, name="person_items"),
    path("s/<str:scope>/replies/", replies.replies, name="replies"),
    path("s/<str:scope>/replies/<str:login>/", replies.person_replies, name="person_replies"),
    path(
        "s/<str:scope>/replies/<str:login>/badge/",
        replies.reply_badge_share,
        name="reply_badge_share",
    ),
    path("s/<str:scope>/chart/<str:name>.svg", charts.chart, name="chart"),
    path("s/<str:scope>/chart/<str:name>.json", charts.chart_json, name="chart_json"),
    path("s/<str:scope>/share/<str:name>/", charts.chart_share, name="chart_share"),
    path("s/<str:scope>/data/<str:name>", exports.export_table, name="export"),
    path("documents/<int:pk>/", documents.document, name="document"),
    path("documents/<int:pk>/progress.json", documents.document_progress, name="document_progress"),
    path("documents/<int:pk>/download/", documents.document_download, name="document_download"),
    path("messages/", documents.messages_page, name="messages"),
    path("messages/read/", documents.messages_read, name="messages_read"),
    path("messages/<int:pk>/", documents.message_open, name="message_open"),
    path("badge/s/<str:scope>.svg", badges.public_badge, name="public_badge"),
    path("badge/<str:token>.svg", badges.badge, name="badge"),
    path("badge/s/<str:scope>.<str:extension>", badges.public_badge, name="public_badge_as"),
    path("badge/<str:token>.<str:extension>", badges.badge, name="badge_as"),
    path(
        "badge/s/<str:scope>/replies/<str:login>.svg",
        replies.public_reply_badge,
        name="public_reply_badge",
    ),
    path(
        "badge/s/<str:scope>/replies/<str:login>.<str:extension>",
        replies.public_reply_badge,
        name="public_reply_badge_as",
    ),
    path("badge/<str:token>/replies/<str:login>.svg", replies.reply_badge, name="reply_badge"),
    path(
        "badge/<str:token>/replies/<str:login>.<str:extension>",
        replies.reply_badge,
        name="reply_badge_as",
    ),
]
if settings.DEBUG_TOOLBAR:
    from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns += debug_toolbar_urls()
