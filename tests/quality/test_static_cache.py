"""Browsers never keep an old script or stylesheet: static files are named by their content."""

import re
from pathlib import Path

from community_insights import settings as site_settings

ROOT = Path(__file__).parents[2]
NGINX = (ROOT / "docker" / "nginx.conf").read_text()


def test_static_files_are_named_with_a_hash_of_their_content():
    """The production storage writes style.4f3a1c2b9d0e.css; the tests use plain names."""
    backend = site_settings.STORAGES["staticfiles"]["BACKEND"]
    assert backend == "whitenoise.storage.CompressedManifestStaticFilesStorage"


def test_nginx_keeps_files_with_a_hash_for_a_year():
    """A name with a hash of 12 hexadecimal digits never changes its content."""
    block = re.search(r'location ~ "\^/static/[^"]*\[0-9a-f\]\{12\}[^"]*" \{(.*?)\}', NGINX, re.S)
    assert block, "a location for the names with a hash"
    assert "expires 1y;" in block.group(1)
    assert "immutable" in block.group(1)


def test_nginx_asks_again_for_files_without_a_hash():
    """Other static files, such as those of an old page, are checked each time."""
    block = re.search(r"location /static/ \{(.*?)\}", NGINX, re.S)
    assert block
    assert 'Cache-Control "no-cache"' in block.group(1)
    assert "expires 7d" not in NGINX, "a week kept old scripts after a deploy"
