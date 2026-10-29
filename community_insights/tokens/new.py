"""Addresses of GitHub that open the form of a new token, filled in for this site."""

from datetime import date
from urllib.parse import urlencode

NEW_TOKEN = "https://github.com/settings/personal-access-tokens/new"
# what private repositories need; public ones need no permission
PRIVATE_PERMISSIONS = {"pull_requests": "read", "issues": "read", "metadata": "read"}
MONTH, YEAR = 30, 365  # GitHub allows 1 to 366 days


def new_token_url(days: int, host: str, today: date, private: bool = False) -> str:
    """The form of GitHub for a fine-grained token that reads for this site.

    GitHub fills in the name, the description, the expiration and the permissions;
    people check them and create the token.

    Args:
        days: How long the token works, 1 to 366.
        host: The host name of this site, for the description.
        today: The day, which makes the name unique: GitHub refuses a name twice.
        private: Whether private repositories are read, which needs permissions.

    Returns:
        The address.

    Examples:
        >>> new_token_url(30, "insight.pycal.org", date(2026, 10, 29))
        'https://github.com/settings/personal-access-tokens/new?name=Community+Insights+2026-10-29&description=Reads+pull+requests+and+issues+for+insight.pycal.org&expires_in=30'
    """
    parameters = {
        "name": f"Community Insights {today.isoformat()}",
        "description": f"Reads pull requests and issues for {host}",
        "expires_in": days,
    }
    if private:
        parameters |= PRIVATE_PERMISSIONS
    return f"{NEW_TOKEN}?{urlencode(parameters)}"
