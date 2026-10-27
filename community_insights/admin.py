"""Every table of the site in the Django admin, to browse the database."""

from django.apps import apps
from django.contrib import admin
from django.db import models

SECRET_FIELDS = {"token", "badge_token"}  # never shown in the admin
COLUMNS = 8


class BrowseAdmin(admin.ModelAdmin):
    """The columns, search and filters of a model, derived from its fields."""

    def fields_of(self) -> list[models.Field]:
        """The fields shown: the concrete ones without the secrets.

        Returns:
            The fields of the model in their order.
        """
        return [
            f
            for f in self.model._meta.concrete_fields
            if f.name not in SECRET_FIELDS
            and not isinstance(f, models.TextField | models.JSONField)
        ]

    def get_list_display(self, request):
        """The first fields of the model as the columns of the list.

        Args:
            request: The request.

        Returns:
            The names of the columns.
        """
        return [f.name for f in self.fields_of()][:COLUMNS] or ["__str__"]

    def get_search_fields(self, request):
        """The text fields of the model can be searched.

        Args:
            request: The request.

        Returns:
            The names of the fields searched.
        """
        return [f.name for f in self.fields_of() if isinstance(f, models.CharField)]

    def get_list_filter(self, request):
        """Filters for the yes/no, choice and date fields.

        Args:
            request: The request.

        Returns:
            The names of at most five fields to filter by.
        """
        return [
            f.name
            for f in self.fields_of()
            if isinstance(f, models.BooleanField | models.DateTimeField) or f.choices
        ][:5]

    def get_exclude(self, request, obj=None):
        """The secrets are not in the forms.

        Args:
            request: The request.
            obj: The object shown, None for a new one.

        Returns:
            The names of the fields left out.
        """
        return [name for name in SECRET_FIELDS if hasattr(self.model, name)]


for model in apps.get_app_config("community").get_models():
    admin.site.register(model, BrowseAdmin)
