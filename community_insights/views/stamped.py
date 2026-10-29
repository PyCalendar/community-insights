"""Images drawn from the data, kept until the data changes and sent again only if needed."""

import functools
import hashlib

from django.core.cache import cache
from django.http import HttpResponse, HttpResponseNotModified
from django.utils import timezone, translation
from django.utils.cache import add_never_cache_headers, patch_cache_control, patch_vary_headers
from django.utils.http import parse_etags

from .. import data_stamp


def key(request, view: str, stamp: str) -> str:
    """What the image depends on, as a hash: the data, the address, who asks and how.

    Args:
        request: The request: its address with the parameters, user, language, time zone.
        view: The name of the view.
        stamp: The stamp of the data (data_stamp.stamp).

    Returns:
        A hexadecimal hash.
    """
    parts = [
        stamp,
        view,
        request.get_full_path(),
        str(request.user.pk) if request.user.is_authenticated else "",
        translation.get_language() or "",
        timezone.get_current_timezone_name(),
    ]
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()


def stamped(view):
    """Keep what the view answers until the data changes; answer with an ETag.

    A browser that has the image asks with ``If-None-Match`` and gets ``304 Not Modified``.
    Another one gets the image from the cache, without drawing it again. Only answers with
    the status 200 are kept. Without a stamp (cachalot off) the view answers every time.

    Args:
        view: A view that answers a GET with an image or data.

    Returns:
        The view, kept.
    """

    @functools.wraps(view)
    def wrapper(request, *args, **kwargs):
        stamp = data_stamp.stamp()
        if stamp is None or request.method not in ("GET", "HEAD"):
            response = view(request, *args, **kwargs)
            add_never_cache_headers(response)
            return response
        found = key(request, view.__name__, stamp)
        etag = f'"{found}"'
        kept = cache.get(f"stamped:{found}")
        if kept is None:
            response = view(request, *args, **kwargs)
            if response.status_code != 200:
                add_never_cache_headers(response)
                return response
            kept = (response.content, response["Content-Type"], response.get("Cache-Control"))
            cache.set(f"stamped:{found}", kept, data_stamp.KEEP)
        content, content_type, cache_control = kept
        if etag in parse_etags(request.headers.get("If-None-Match", "")):
            response = HttpResponseNotModified()
        else:
            response = HttpResponse(content, content_type=content_type)
        response["ETag"] = etag
        if cache_control:  # chosen by the view, such as the 15 minutes of a badge
            response["Cache-Control"] = cache_control
        else:  # the browser keeps it, but asks each time: 304 while the data is the same
            patch_cache_control(response, no_cache=True)
            if request.user.is_authenticated:
                patch_cache_control(response, private=True)
        patch_vary_headers(response, ("Cookie",))
        return response

    return wrapper
