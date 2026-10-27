from django.conf import settings
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import include, path
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
    explore,
    exports,
    fetch,
    items,
    pages,
    statistics,
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
    path("", pages.home, name="home"),
    path("about/", pages.about, name="about"),
    path("explore/", explore.explore, name="explore"),
    path("explore/submit/", explore.submit, name="explore_submit"),
    path("dashboard/", dashboard.dashboard, name="dashboard"),
    path("dashboard/classes/", classes.classes, name="classes"),
    path("dashboard/cache/", cache.cache, name="cache"),
    path("dashboard/github/", access.github_access, name="github_access"),
    path("dashboard/downloads/", fetch.downloads, name="downloads"),
    path("projects/<int:pk>/delete/", dashboard.project_delete, name="project_delete"),
    path("projects/<int:pk>/rename/", dashboard.project_rename, name="project_rename"),
    path("s/<str:scope>/", statistics.overview, name="overview"),
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
    path("s/<str:scope>/chart/<str:name>.svg", charts.chart, name="chart"),
    path("s/<str:scope>/data/<str:name>", exports.export_table, name="export"),
    path("badge/s/<str:scope>.svg", badges.public_badge, name="public_badge"),
    path("badge/<str:token>.svg", badges.badge, name="badge"),
]
if settings.DEBUG_TOOLBAR:
    from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns += debug_toolbar_urls()
