from django.apps import AppConfig


class CommunityConfig(AppConfig):
    """The Django app with the pages, the statistics and the fetching.

    The label stays ``community``: it names the tables, the migrations and the
    addresses of the admin, so databases made before the merge of the packages
    keep working.
    """

    name = "community_insights"
    label = "community"

    def ready(self):
        """Register the checks of the configuration."""
        from . import checks  # noqa: F401
