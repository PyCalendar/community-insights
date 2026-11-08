from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """manage.py name_site: give the site of SITE_ID the name of SITE_NAME, at each start."""

    help = "Name the site (django.contrib.sites) after SITE_NAME; without it, keep its name."

    def handle(self, *args, **options):
        """Name the first site, which mails and pages use, such as the subjects of mails.

        Args:
            *args: The positional arguments Django passes.
            **options: The other options of the command.
        """
        name = settings.SITE_NAME.strip()
        if not name:
            return
        site, _created = Site.objects.get_or_create(
            pk=settings.SITE_ID, defaults={"domain": "example.com", "name": name}
        )
        if site.name != name:
            site.name = name
            site.save(update_fields=["name"])
        self.stdout.write(f"The site is named {name}.")
