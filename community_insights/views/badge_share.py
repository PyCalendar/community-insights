"""What the card of a badge needs (templates/community/_badge_share.html): one for all badges."""

from django.utils.http import urlencode


def badge_format(request) -> str:
    """The format of the image of a badge the page shows: ``format=png``, else SVG.

    Args:
        request: The request.

    Returns:
        ``svg`` or ``png``.
    """
    return "png" if request.GET.get("format") == "png" else "svg"


def format_address(request, image_format: str) -> str:
    """The address of this page with another format of the badge, with the other parameters.

    Args:
        request: The request.
        image_format: ``svg`` or ``png``.

    Returns:
        The query, starting with ``?``.
    """
    query = request.GET.copy()
    query["format"] = image_format
    return "?" + query.urlencode()


def badge_share(request, path_of, page: str, alt: str) -> dict | None:
    """The addresses of a badge and the page it links to, for its card.

    Args:
        request: The request; ``format=png`` chooses PNG.
        path_of: Gives the path of the badge for an extension (``svg``, ``png``, ``json``);
            None if there is no badge.
        page: The full address of the page the badge links to.
        alt: The text of the image.

    Returns:
        ``preview`` (the path, as this site loads its images), ``image`` (the full address
        to copy), ``json_url``, ``page``, ``alt``, ``image_format``, ``svg_url`` and
        ``png_url`` (this page in the other format); None without a badge.
    """
    image_format = badge_format(request)
    path = path_of(image_format)
    if not path:
        return None
    json_path = path_of("json")
    return {
        "preview": path,
        "image": request.build_absolute_uri(path),
        "json_url": request.build_absolute_uri(json_path) if json_path else None,
        "page": page,
        "alt": alt,
        "image_format": image_format,
        "svg_url": format_address(request, "svg"),
        "png_url": format_address(request, "png"),
    }


def with_query(path: str | None, **parameters) -> str | None:
    """A path with parameters, those that are set.

    Args:
        path: The path; None for none.
        **parameters: The parameters; those that are false are left out.

    Returns:
        The path with ``?...``; None for None.

    Examples:
        >>> with_query("/b.svg", number="1", drafts=None), with_query("/b.svg")
        ('/b.svg?number=1', '/b.svg')
    """
    if path is None:
        return None
    found = {k: v for k, v in parameters.items() if v}
    return f"{path}?{urlencode(found)}" if found else path
