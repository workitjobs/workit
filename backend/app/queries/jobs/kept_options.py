"""
The filter row's options (GET /jobs/facets and GET /jobs/locations), kept in
this process until the job postings change (KAN-916).

WHY HERE, NOT IN NEXT. The Jobs page asked for both on every filter change
and every search, with `revalidate` set, but production's Next keeps no
data cache (frontend/open-next.config.ts), so each ask reached this API and
ran its counting queries again: facets 1.6 to 2.0 s, locations 0.8 to 6.7 s
on 2026-11-18. They change only when the import, the scraper or a closing
writes job_postings, so they are kept here instead.

KEPT UNTIL THE POSTINGS CHANGE. Each kept answer carries the feed's version
it was made from, the newest job_postings.updated_at (the import, the
scraper's descriptions and every closing set it, as home.py relies on). The
version is read at most once a VERSION_CHECK_SECONDS per process, so a
burst of filter changes costs no query at all, and an import shows within a
minute. KEEP_SECONDS bounds the rest: the "past 7 days" counts and the
start terms still open move with the clock. Each process keeps its own, as
home.py's does: two containers each count once per change.

The version is read before the answer is made, so an import that lands
while it is made gives a newer version at the next check, and the answer is
made again: it can be a minute stale, never stuck.
"""

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.jobs import Job_Post

# How often a process asks whether the job postings changed.
VERSION_CHECK_SECONDS = 60
# The longest a kept answer is served, changed postings or not.
KEEP_SECONDS = 3600

# name -> (the answer, the version it was made from, when it was made)
_kept: dict[str, tuple[Any, Any, float]] = {}
# The last version read, and when.
_version: tuple[Any, float] | None = None
# One maker per name at a time: the requests that arrive while an answer is
# being made wait for it rather than run the same counting queries beside it.
_locks: dict[str, asyncio.Lock] = {}


async def feed_version(db: AsyncSession) -> Any:
    """The newest job_postings.updated_at: any import, description or closing moves it."""
    return await db.scalar(select(func.max(Job_Post.updated_at)))


async def _current_version(db: AsyncSession, now: float) -> Any:
    global _version
    if _version is None or now - _version[1] >= VERSION_CHECK_SECONDS:
        _version = (await feed_version(db), now)
    return _version[0]


async def kept_options(
    db: AsyncSession, name: str, make: Callable[[AsyncSession], Awaitable[Any]]
) -> Any:
    """`make(db)`'s answer, kept under `name` until the feed's version moves
    or KEEP_SECONDS pass."""
    lock = _locks.setdefault(name, asyncio.Lock())
    async with lock:
        now = time.monotonic()
        version = await _current_version(db, now)
        hit = _kept.get(name)
        if hit is not None and hit[1] == version and now - hit[2] < KEEP_SECONDS:
            return hit[0]
        answer = await make(db)
        _kept[name] = (answer, version, now)
        return answer


def forget() -> None:
    """Drops every kept answer and the version read (tests)."""
    global _version
    _kept.clear()
    _locks.clear()
    _version = None
