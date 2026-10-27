from django.utils import timezone
from tz_detect.middleware import TimezoneMiddleware


class SafeTimezoneMiddleware(TimezoneMiddleware):
    """The time zone of the browser (django-tz-detect).

    Its endpoint stores any text the browser sends: a time zone that does not exist is forgotten
    and the page is shown in UTC, instead of failing on every page.
    """

    def process_request(self, request):
        """Use the time zone of the browser; forget one that does not exist.

        Args:
            request: The request.

        Returns:
            None, so that the request goes on.
        """
        try:
            return super().process_request(request)
        except Exception:  # pytz.UnknownTimeZoneError and others
            request.session.pop("detected_tz", None)
            timezone.deactivate()
            return None
