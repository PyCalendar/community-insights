"""A test client that follows a page of projects to its public address, as a browser does."""

import re

from django.test import Client

PROJECT_PAGE = re.compile(r"^/s/(\d+(-\d+)*|all)/")
PUBLIC_PAGE = re.compile(r"^/s/[^/]+/")


class ScopeClient(Client):
    """The client of the tests: a read of ``/s/<number>/...`` follows the redirect to the same
    page of the public scope (``views.scope.public_address``), so a test of a page shows what a
    person sees. Other redirects are returned, as with Django's client.

    ``tests/pages/test_public_address.py`` tests the redirect itself with Django's client.
    """

    def get(self, path, data=None, follow=False, secure=False, *, headers=None, **extra):
        """Read a page; a project page leads to its public address.

        Args:
            path: The address.
            data: The parameters.
            follow: Whether to follow all redirects.
            secure: Whether it is HTTPS.
            headers: The headers.
            **extra: Further parts of the request.

        Returns:
            The response.
        """
        response = super().get(path, data, follow=follow, secure=secure, headers=headers, **extra)
        if follow or response.status_code != 302 or not PROJECT_PAGE.match(str(path)):
            return response
        location = response["Location"]
        same = PROJECT_PAGE.sub("/s/X/", str(path).split("?")[0])
        if PUBLIC_PAGE.sub("/s/X/", location.split("?")[0]) != same:
            return response  # another redirect, such as to the sign in
        return super().get(location, secure=secure, headers=headers, **extra)
