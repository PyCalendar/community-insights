"""Where and how many fetch jobs run: FETCH_WORKER and FETCH_CONCURRENCY."""

import asyncio
import threading
import time

from asgiref.sync import async_to_sync, sync_to_async
from django.conf import settings
from django.db import connections
from django.utils import timezone

from ..cleanup import after_fetching, clean_up_daily
from . import jobs, modes
from .runner import JobRunner

SLEEP = 2.0  # seconds between looks at an empty queue

_thread: threading.Thread | None = None
_lock = threading.Lock()


async def work_async(once: bool = False, make_client=None) -> int:
    """Run the queued jobs, highest priority first.

    Run jobs, highest priority first, up to FETCH_CONCURRENCY at the same time; with once, until
    the queue is empty. The number of jobs run.
    """
    concurrency = max(1, getattr(settings, "FETCH_CONCURRENCY", 4))
    running: set[asyncio.Task] = set()
    count = 0
    while True:
        while len(running) < concurrency:
            job = await sync_to_async(jobs.claim_next)()
            if job is None:
                break
            running.add(asyncio.create_task(JobRunner(job, make_client).run()))
            count += 1
        if not running:
            if once:
                return count
            await sync_to_async(clean_up_daily)()
            await asyncio.sleep(SLEEP)
            continue
        done, running = await asyncio.wait(running, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()  # a job never raises: its errors end the job
        if not running and not await sync_to_async(jobs.has_ready_jobs)():
            # data was added and nothing writes now: keep the database small
            await sync_to_async(after_fetching)()


def work(once: bool = False, make_client=None) -> int:
    """work_async from synchronous code."""
    return async_to_sync(work_async)(once, make_client)


def run(job, make_client=None):
    """Run one claimed job now, from synchronous code."""
    return async_to_sync(JobRunner(job, make_client).run)()


MAX_WAIT = 300  # seconds a thread sleeps before it looks at the queue again


def _thread_main() -> None:
    """Run the queue until it is empty; sleep while jobs wait for a rate limit."""
    try:
        while True:
            work(once=True)
            waiting = jobs.next_waiting()
            if waiting is None:
                return
            seconds = (waiting - timezone.now()).total_seconds()
            time.sleep(min(max(seconds, 1), MAX_WAIT))
    finally:
        connections.close_all()


def start_worker() -> None:
    """Start the worker for the queued jobs, if this process runs it.

    The mode of FETCH_WORKER decides (see modes.py): ``internal`` runs the queue
    in a thread of this process, ``inline`` now (tests); the external modes leave
    it to ``manage.py fetch_worker``. Unused data is cleaned up once a day.
    """
    clean_up_daily()
    found = modes.mode()
    if found == modes.INLINE:
        work(once=True)
    elif found == modes.INTERNAL:
        global _thread
        with _lock:
            if _thread is None or not _thread.is_alive():
                _thread = threading.Thread(target=_thread_main, daemon=True, name="fetch-worker")
                _thread.start()
