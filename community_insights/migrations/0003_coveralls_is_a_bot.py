from django.db import migrations


def add_coveralls(apps, schema_editor):
    """Add coveralls to the handles of the classes with the rule "is a bot"."""
    PersonClass = apps.get_model("community", "PersonClass")
    for person_class in PersonClass.objects.filter(rules__kind="bot").distinct():
        rule = person_class.rules.filter(kind="handle").first()
        if rule is None:
            person_class.rules.create(kind="handle", value="coveralls")
        elif "coveralls" not in rule.value.lower().split():
            rule.value = f"{rule.value} coveralls".strip()
            rule.save()


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0002_profile_horizon_europe_job_choices"),
    ]

    operations = [
        migrations.RunPython(add_coveralls, migrations.RunPython.noop),
    ]
