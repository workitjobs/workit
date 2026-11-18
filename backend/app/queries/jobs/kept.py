"""
Scored lists kept in this process, so a return visit reads the list it saw
instead of scoring every job again: Home's three lists (KAN-425) and each
Best Match list (KAN-915), which Load More, Back and a repeat read.

KEPT UNTIL IT GOES STALE. A result is kept under what it was made from
(made_from): the bank's updated_at (every entry, bullet or skill change
sets it, services/bank.py), the newest job_postings.updated_at (the import,
its embeddings and every closing set it), and the jobs on the applicant's
Tracker, which the Jobs page leaves out (JobFilters.tracked_by). Any change
makes a new key, so a kept result is never served after one; each Kept's
`seconds` bounds the rest (a posting's freshness and a Date Posted window
move with the clock). Each process keeps its own: a container's lasts while
it runs. Reading the key costs one small query.
"""

import dataclasses
import datetime
import json
import time
import uuid
from collections import OrderedDict
from collections.abc import Hashable

from sqlalchemy import Text, cast, func, select
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import dto
from app.models.applications import Job_Application
from app.models.bank import Experience_Bank
from app.models.jobs import Job_Post
from app.queries.jobs.filters import JobFilters
from app.schemas.jobs import ScoredJob


class Kept[T]:
    """Results by key, each served while younger than `seconds`; past
    `size`, the least recently read goes first."""

    def __init__(self, seconds: float, size: int) -> None:
        self.seconds = seconds
        self.size = size
        self._items: OrderedDict[Hashable, tuple[float, T]] = OrderedDict()

    def get(self, key: Hashable) -> T | None:
        hit = self._items.get(key)
        if hit is None or time.monotonic() - hit[0] > self.seconds:
            return None
        self._items.move_to_end(key)
        return hit[1]

    def put(self, key: Hashable, value: T) -> None:
        self._items[key] = (time.monotonic(), value)
        self._items.move_to_end(key)
        while len(self._items) > self.size:
            self._items.popitem(last=False)

    def clear(self) -> None:
        self._items.clear()


# Best Match's lists (GET /jobs/recommended): each applicant's whole scored
# list per filters, before min_match and the page, as long as Home's.
# A list is up to CANDIDATES (500) jobs, about 2.5 MB, so 32 lists stay
# under 100 MB of the container's 1 GiB.
BEST_MATCH_SECONDS = 600
BEST_MATCH_SIZE = 32
BEST_MATCH: Kept[list[ScoredJob]] = Kept(BEST_MATCH_SECONDS, BEST_MATCH_SIZE)


async def made_from(db: AsyncSession, applicant_id: uuid.UUID) -> tuple:
    """What a kept result was made from, read in one query: the bank's
    updated_at, the newest job posting change, and a hash of the jobs on
    this applicant's Tracker (saved, applied and after), which the Jobs
    page and Top Matches leave out: a Save changes the key. Only those
    stages: a key for filters that leave out other applications (auto
    apply's no_application_by) would need them all."""
    tracked = (
        select(func.md5(func.coalesce(func.string_agg(
            cast(Job_Application.job_id, Text),
            aggregate_order_by(",", Job_Application.job_id),
        ), "")))
        .where(
            Job_Application.applicant_id == applicant_id,
            Job_Application.stage.not_in(dto.ON_THE_JOBS_PAGE),
        )
        .scalar_subquery()
    )
    row = (await db.execute(select(
        select(Experience_Bank.updated_at)
        .where(Experience_Bank.applicant_id == applicant_id)
        .scalar_subquery(),
        select(func.max(Job_Post.updated_at)).scalar_subquery(),
        tracked,
    ))).one()
    return tuple(row)


def filters_key(filters: JobFilters) -> str:
    """The filters as one hashable value. Date Posted's cutoff is now minus
    its days, so it moves on every request: it counts to the hour, which
    lets Load More and Back within the hour read the list they saw, while
    the Kept's seconds bound how stale its cutoff can be."""
    since = filters.posted_since
    if since is not None:
        since = since.replace(minute=0, second=0, microsecond=0)
    fields = dataclasses.asdict(dataclasses.replace(filters, posted_since=since))
    return json.dumps(fields, sort_keys=True, default=_plain)


def _plain(value: object) -> str:
    if isinstance(value, datetime.datetime | uuid.UUID):
        return str(value)
    raise TypeError(f"{type(value).__name__} in JobFilters has no key")
