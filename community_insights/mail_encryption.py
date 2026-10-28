"""How the site encrypts the connection to the mail server."""

SSL_PORT = 465  # SMTPS: TLS from the first byte, also called SSL/TLS


def encryption(port: int, ssl: bool | None, tls: bool | None) -> tuple[bool, bool]:
    """Choose EMAIL_USE_SSL and EMAIL_USE_TLS: what is set, else what the port speaks.

    Port 465 speaks TLS from the first byte (``EMAIL_USE_SSL``); the other ports, such as
    587, start in plain text and switch with STARTTLS (``EMAIL_USE_TLS``). A server that
    is spoken to the wrong way closes the connection: ``SMTPServerDisconnected``.

    Args:
        port: EMAIL_PORT.
        ssl: EMAIL_USE_SSL, or None if it is not set.
        tls: EMAIL_USE_TLS, or None if it is not set.

    Returns:
        EMAIL_USE_SSL and EMAIL_USE_TLS. Both are True only if both are set so; the check
        ``community.E002`` refuses that.

    Examples:
        >>> encryption(587, None, None)
        (False, True)
        >>> encryption(465, None, None)
        (True, False)
        >>> encryption(465, False, True)
        (False, True)
        >>> encryption(25, None, False)
        (False, False)
    """
    if ssl is None:
        ssl = port == SSL_PORT and not tls
    if tls is None:
        tls = not ssl
    return ssl, tls
