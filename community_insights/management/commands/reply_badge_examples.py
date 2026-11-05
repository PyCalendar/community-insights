from pathlib import Path

from django.core.management.base import BaseCommand

from community_insights.reply_badges import EXAMPLES, reply_spec

DEFAULT_FOLDER = Path(__file__).parents[3] / "docs" / "reference" / "badges"


def example_files() -> dict[str, bytes]:
    """The example badges of replies for the documentation, by their file names.

    Returns:
        The SVG of each colour, such as ``replies-green.svg``.
    """
    return {
        f"replies-{name}.svg": reply_spec("kim", person).svg() for name, person in EXAMPLES.items()
    }


class Command(BaseCommand):
    """manage.py reply_badge_examples: write the badges of replies of the documentation."""

    help = "Write an example badge of replies of each colour for the documentation."

    def add_arguments(self, parser):
        """The folder to write into.

        Args:
            parser: The parser of the arguments of the command.
        """
        parser.add_argument("folder", nargs="?", default=str(DEFAULT_FOLDER))

    def handle(self, *args, folder, **options):
        """Write the SVG files.

        Args:
            *args: The positional arguments Django passes.
            folder: Where to write them.
            **options: The other options of the command.
        """
        target = Path(folder)
        target.mkdir(parents=True, exist_ok=True)
        for name, content in example_files().items():
            (target / name).write_bytes(content)
            self.stdout.write(str(target / name))
