"""The encryption of the connection to the mail server: SSL for port 465, else STARTTLS."""

import pytest

from community_insights import checks
from community_insights.mail_encryption import encryption


@pytest.mark.parametrize(
    ("port", "ssl", "tls", "expected"),
    [
        (587, None, None, (False, True)),  # STARTTLS, as before
        (25, None, None, (False, True)),
        (465, None, None, (True, False)),  # SSL/TLS, such as smtp.zoho.com:465
        (465, True, None, (True, False)),
        (465, None, True, (False, True)),  # STARTTLS asked for on 465
        (465, False, None, (False, True)),
        (587, True, None, (True, False)),  # SSL asked for on another port
        (587, None, False, (False, False)),  # no encryption, such as a local relay
        (465, False, False, (False, False)),
        (465, True, True, (True, True)),  # refused by the check
    ],
)
def test_encryption(port, ssl, tls, expected):
    """What is set wins; otherwise port 465 speaks SSL and the others STARTTLS."""
    assert encryption(port, ssl, tls) == expected


def test_both_encryptions_are_refused(settings):
    """A mail server speaks only one of them: the site does not start."""
    settings.EMAIL_USE_SSL = settings.EMAIL_USE_TLS = True
    settings.EMAIL_PORT = 465
    (error,) = checks.mail_encryption()
    assert error.id == "community.E002"
    assert "EMAIL_PORT=465" in error.msg
    assert error.hint.endswith("#community_insights.errors.configuration.EmailEncryptionConflict")


@pytest.mark.parametrize(("ssl", "tls"), [(True, False), (False, True), (False, False)])
def test_one_encryption_passes(settings, ssl, tls):
    """One encryption, or none, passes the check."""
    settings.EMAIL_USE_SSL, settings.EMAIL_USE_TLS = ssl, tls
    assert checks.mail_encryption() == []
