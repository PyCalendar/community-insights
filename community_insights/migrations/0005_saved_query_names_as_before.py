import re

from django.db import migrations

# the names of the variables before the names of the command line tool came back
RENAMED = {
    "login": "user_handle",
    "name": "user_name",
    "location": "user_location",
    "country": "user_country",
    "horizon_europe": "user_horizon_europe",
    "class": "user_class",
    "bot": "user_bot",
    "prs_opened": "prs_total",
    "prs_closed": "prs_unmerged",
    "comments": "comments_total",
    "reviews": "prs_reviewed",
    "activity": "activity_total",
    "response_hours": "hours_to_respond",
    "active_months": "months_active",
}
NAME = re.compile(r'"[^"]*"|\'[^\']*\'|\b[a-z_]+\b')


def rename(text: str) -> str:
    """The text with the old names of variables replaced; text in quotes stays."""
    return NAME.sub(lambda m: RENAMED.get(m.group(0), m.group(0)), text)


def forwards(apps, schema_editor):
    """Rename the variables in the saved queries."""
    SavedQuery = apps.get_model("community", "SavedQuery")
    for query in SavedQuery.objects.all():
        for field in ("where", "sort", "columns", "group", "chart"):
            setattr(query, field, rename(getattr(query, field)))
        query.save()


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0004_saved_query_time_range"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
