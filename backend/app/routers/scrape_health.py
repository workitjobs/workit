"""
The scraper's health for admins (KAN-879): how the scheduled scrape is doing,
read from the worker's own tables (queries/scrape_health.py).

GET /admin/scrape-health  ?days=1..90 (default 14)
    Kept in memory for 10 minutes per `days` (queries KEEP_SECONDS), so
    many opens cost one read; `read_at` says when it was read.
    `last_import_at`: the newest job posting write, the trace of the
    scheduled feed import (scrape.yml), which the worker has not replaced
    yet.
    `boards`: enabled boards now, how many are failing (a failed read since
    their last good one), resting (rest_until ahead) and stale (unread for
    2 days or never read), and the backlog: tasks
    pending and claimed, and when the oldest pending one was made.
    `systems`: per hiring system, the enabled boards, how many were ever
    read, and the newest read.
    `days`: per day (UTC) per hiring system, board reads done and failed,
    their mean seconds, and the jobs first seen on its boards.
    `failing`: up to 25 failing boards, most failures first, each with its
    last error (credentials already stripped by scraper/tasks.py).
    `errors`: the failed reads of those `days` by reason (the error's text
    before its first ": "), most boards first: the boards and reads that
    failed for it, its newest time, and the newest read's board and whole
    error as an example. It holds boards `failing` lacks: a failed publish
    does not count as a board failure.
    Admins only (WORKIT_ADMINS, 403 to anyone else), as /admin/fill-health.
"""

import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_admin
from app.queries.scrape_health import scrape_health
from app.schemas.auth import AuthenticatedAccount

router = APIRouter(tags=["scrape-health"])


class BoardsSummary(BaseModel):
    boards: int
    failing: int
    resting: int
    stale: int
    pending: int
    claimed: int
    oldest_pending_at: datetime.datetime | None


class SystemBoards(BaseModel):
    ats: str
    boards: int
    read: int
    last_read_at: datetime.datetime | None


class ScrapeDay(BaseModel):
    day: str
    ats: str
    done: int
    failed: int
    mean_seconds: float | None
    new_jobs: int


class FailingBoard(BaseModel):
    ats: str
    token: str
    company: str
    consecutive_failures: int
    last_error: str | None


class ErrorGroup(BaseModel):
    reason: str
    boards: int
    reads: int
    last_at: datetime.datetime
    ats: str
    token: str
    company: str
    error: str | None


class ScrapeHealth(BaseModel):
    read_at: datetime.datetime
    last_import_at: datetime.datetime | None
    boards: BoardsSummary
    systems: list[SystemBoards]
    days: list[ScrapeDay]
    failing: list[FailingBoard]
    errors: list[ErrorGroup]


@router.get("/admin/scrape-health", response_model=ScrapeHealth)
async def admin_scrape_health(
    days: int = Query(default=14, ge=1, le=90),
    _admin: AuthenticatedAccount = Depends(get_admin),
    db: AsyncSession = Depends(get_session),
) -> ScrapeHealth:
    return ScrapeHealth(**await scrape_health(db, days=days))
