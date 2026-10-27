"""Made up data to try the site without GitHub (`make run-prepare`)."""

from .client import DemoClient

# the made up repository: never on GitHub, so it is not tested or explored like the others
DEMO = "demo/community"

__all__ = ["DEMO", "DemoClient"]
