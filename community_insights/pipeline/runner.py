from asgiref.sync import sync_to_async

from .. import errors, github
from ..github.anonymous import AnonymousClient
from ..models import FetchJob
from ..sync import Syncer
from ..sync.sources import AnonymousSource
from ..tokens import TokenPool, entries_for
from . import jobs

PROGRESS_EVERY = 10  # items between updates of the progress in the database


class JobRunner:
    """Runs one claimed job.

    Runs one claimed job: reads its repository with the tokens of its user, within its limit,
    shows the progress, stops when it is cancelled, and ends it with the outcome.
    """

    def __init__(self, job: FetchJob, make_client=None):
        """Run a fetch job: read the repository with the tokens of its user.

        Args:
            job: The claimed job.
            make_client: Makes the GitHub client of a token, ``github.Client`` if None; tests give a
                fake one.
        """
        self.job = job
        self.make_client = make_client or github.Client
        self.items = 0  # read and not yet added to the job
        self.pool: TokenPool | AnonymousSource | None = None

    async def on_item(self) -> None:
        """Count an item read; the progress is written every few items."""
        self.items += 1
        if self.items % PROGRESS_EVERY == 0:
            await sync_to_async(FetchJob.objects.filter(pk=self.job.pk).update)(
                items_done=self.job.items_done + self.items,
                points_used=self.job.points_used + (self.pool.points if self.pool else 0),
            )

    async def check(self) -> None:
        """Stop with FetchCancelled when the job was cancelled.

        Raises:
            FetchCancelled: If somebody cancelled the job.
        """
        if await sync_to_async(jobs.cancel_requested)(self.job):
            raise errors.FetchCancelled("What was read is kept.")

    def account(self) -> None:
        """Add the items and points of this run to the job."""
        self.job.items_done += self.items
        self.job.points_used += self.pool.points if self.pool else 0
        self.items = 0
        if self.pool:
            self.pool.points = 0

    async def run(self) -> FetchJob:
        """Read the repository and end the job with the outcome; it never raises.

        Returns:
            The job, ended or queued again to wait for a rate limit.
        """
        job = self.job
        budget = None if job.point_limit is None else max(0, job.point_limit - job.points_used)
        try:
            entries = await sync_to_async(entries_for)(job.user, self.make_client)
        except errors.CommunityError as error:
            return await sync_to_async(jobs.finish)(job, FetchJob.FAILED, error)
        # without any token: the requests without a token of this server
        self.pool = TokenPool(entries, budget) if entries else AnonymousSource(AnonymousClient())
        try:
            message = await Syncer(self.pool, self.on_item, self.check).sync(job.repository)
        except errors.FetchCancelled as error:
            return await self.end(FetchJob.CANCELLED, error)
        except errors.FetchLimitReached as error:
            return await self.end(FetchJob.LIMIT, error)
        except errors.AllTokensUsedUp as error:
            self.account()
            return await sync_to_async(jobs.wait)(job, error)
        except Exception as error:  # translated and shown to the user on the page
            return await self.end(FetchJob.FAILED, errors.translate(error))
        finally:
            await self.pool.close()
        return await self.end(FetchJob.DONE, message)

    async def end(self, status: str, outcome) -> FetchJob:
        """End the job with a status and a message or error.

        Args:
            status: The status it ends with.
            outcome: The message, or the error it stopped with.

        Returns:
            The job, saved.
        """
        self.account()
        return await sync_to_async(jobs.finish)(self.job, status, outcome)
