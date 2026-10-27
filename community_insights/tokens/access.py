from allauth.socialaccount.models import SocialToken
from asgiref.sync import async_to_sync, sync_to_async

from .. import github
from ..github.anonymous import AnonymousClient
from ..models import AccessToken, Profile
from .allowance import HourAllowance
from .entry import Entry
from .pool import TokenPool


def mirror_linked_account(user) -> AccessToken | None:
    """The linked GitHub account as the first token.

    The token of the linked GitHub account as an AccessToken, first in the order, so it has the
    same limits and can be shared like the others; gone when the account is unlinked.
    """
    social = (
        SocialToken.objects.filter(account__user=user, account__provider="github")
        .select_related("account")
        .first()
    )
    mirror = AccessToken.objects.filter(user=user, linked=True).first()
    if social is None:
        if mirror is not None:
            mirror.delete()
        return None
    login = social.account.extra_data.get("login", "")
    if mirror is None:
        mirror = AccessToken.objects.create(
            user=user, token=social.token, login=login, label="linked GitHub account", linked=True
        )
        mirror.top()
    elif mirror.token != social.token:
        mirror.token = social.token
        mirror.save(update_fields=["token"])
    return mirror


def entries_for(user, make_client=None, shared: bool = True) -> list[Entry]:
    """The tokens a user may use, in their order.

    The tokens a user may use, in this order: the linked GitHub account, the own tokens, then
    the points others share on this site.
    """
    make_client = make_client or github.Client
    found = []
    signed_in = user is not None and user.is_authenticated
    if signed_in:  # visitors use only what is donated to the site
        allowance = HourAllowance(Profile.of(user))
        mirror_linked_account(user)
        for stored in AccessToken.objects.filter(user=user):
            found.append(Entry(str(stored), make_client(stored.token), stored, allowance=allowance))
    if shared:
        others = AccessToken.objects.filter(max_percent__gt=0, shared_percent__gt=0)
        if signed_in:
            others = others.exclude(user=user)
        for stored in others.order_by("id"):
            found.append(
                Entry(f"shared by {stored.login}", make_client(stored.token), stored, shared=True)
            )
    return found


def points_left(entries: list[Entry], now) -> dict:
    """The points the tokens may use in this hour.

    The points the tokens may use in this hour: own, shared, and whether one has no limit of
    this site (the linked account).
    """
    own = shared = 0
    unlimited = False
    for entry in entries:
        left = entry.left(now)
        github = entry.github_budget(now)
        if left is None:
            if github is None:
                unlimited = True
            else:
                own += github
            continue
        if github is not None:
            left = min(left, github)
        if entry.shared:
            shared += left
        else:
            own += left
    return {"own": own, "shared": shared, "total": own + shared, "unlimited": unlimited}


def pool_for(user, point_limit: int | None = None) -> TokenPool:
    """A pool of the tokens of a user.

    A pool of the tokens of a user (github.Client looked up when called, so tests can replace
    it).
    """
    return TokenPool(entries_for(user, github.Client), point_limit)


ANONYMOUS_READS = ("repository", "repositories", "totals")


def ask(user, read: str, *args):
    """Run a read with the tokens of a user, from synchronous code.

    Run a read of github/reads.py with the tokens of a user, from synchronous code; the
    connections are closed afterwards. Without any token, the reads that work without one use
    the quota of this server.
    """

    async def asking():
        entries = await sync_to_async(entries_for)(user)
        if not entries and read in ANONYMOUS_READS:
            reader = AnonymousClient()
        else:
            reader = TokenPool(entries)
        try:
            return await getattr(reader, read)(*args)
        finally:
            await reader.close()

    return async_to_sync(asking)()


def ask_one(token: str, read: str, *args):
    """Run a read with one token, from synchronous code.

    Run a read with one token, from synchronous code: (result, client), the client to see the
    rate limit and expiration GitHub told.
    """

    async def asking():
        client = github.Client(token)
        try:
            return await getattr(client, read)(*args), client
        finally:
            await client.close()

    return async_to_sync(asking)()
