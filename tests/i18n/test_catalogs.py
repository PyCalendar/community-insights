"""The translations in locale/: complete, with the same placeholders, compiled."""

import re
from pathlib import Path

import polib
import pytest
from django.conf import settings

LOCALE = Path(settings.BASE_DIR) / "locale"
CATALOGS = sorted(LOCALE.glob("*/LC_MESSAGES/*.po"))
PLACEHOLDER = re.compile(r"%\(\w+\)s|%%|<[^>]+>")


def name(path: Path) -> str:
    return str(path.relative_to(LOCALE))


def test_every_language_has_its_catalogs():
    for code, _ in settings.LANGUAGES:
        if code == settings.LANGUAGE_CODE:
            continue
        for domain in ("django", "djangojs"):
            assert (LOCALE / code / "LC_MESSAGES" / f"{domain}.po").exists(), (code, domain)


@pytest.mark.parametrize("path", CATALOGS, ids=name)
def test_everything_is_translated(path):
    catalog = polib.pofile(str(path))
    assert not catalog.untranslated_entries()
    assert not catalog.fuzzy_entries()


@pytest.mark.parametrize("path", CATALOGS, ids=name)
def test_the_placeholders_and_tags_stay(path):
    for entry in polib.pofile(str(path)).translated_entries():
        texts = list(entry.msgstr_plural.values()) if entry.msgid_plural else [entry.msgstr]
        for text in texts:
            assert sorted(PLACEHOLDER.findall(text)) == sorted(PLACEHOLDER.findall(entry.msgid)), (
                entry.msgid
            )


@pytest.mark.parametrize("path", CATALOGS, ids=name)
def test_the_compiled_catalog_is_up_to_date(path):
    """make messages compiles them; the .mo files are in the repository."""
    source = {
        (e.msgid, e.msgid_plural): (e.msgstr, sorted(e.msgstr_plural.items()))
        for e in polib.pofile(str(path)).translated_entries()
    }
    compiled = {
        (e.msgid, e.msgid_plural): (e.msgstr, sorted(e.msgstr_plural.items()))
        for e in polib.mofile(str(path.with_suffix(".mo")))
        if e.msgid
    }
    assert compiled == source
