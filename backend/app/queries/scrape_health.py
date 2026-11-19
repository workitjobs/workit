"""
The scraper's health for admins (KAN-879), behind routers/scrape_health.py:
read only from the worker's own tables (scraper_schedules, scraper_tasks,
job_sources) and job_postings, so it needs no new table and costs the worker
nothing.
"""

import datetime
import time

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dto import job_post_status
from app.models.jobs import Job_Post
from app.models.scraper import Job_Source, Scraper_Schedule, Scraper_Task

# A board unread this long is stale: the worker reads every enabled board daily at least.
STALE_AFTER = datetime.timedelta(days=2)
FAILING_LIMIT = 25
# Admin numbers need not be fresher than this, and job_postings is costly to read (KAN-879).
KEEP_SECONDS = 600

S, T, J = Scraper_Schedule, Scraper_Task, Job_Source


async def boards_summary(db: AsyncSession) -> dict:
    '''counts over enabled boards now: all, failing (a failed read since its last good one), resting
    (rest_until ahead), stale (unread for STALE_AFTER or never read); and the open scraped jobs'''
    now = datetime.datetime.now(datetime.UTC)
    row = (await db.execute(
        select(
            func.count().label("boards"),
            func.count().filter(S.consecutive_failures > 0).label("failing"),
            func.count().filter(S.rest_until > now).label("resting"),
            func.count().filter(
                S.last_read_at.is_(None) | (S.last_read_at < now - STALE_AFTER)
            ).label("stale"),
        ).where(S.enabled.is_(True))
    )).one()
    open_jobs = (await db.execute(
        select(func.count()).select_from(Job_Post).where(
            Job_Post.status == job_post_status.published,
            exists().where(J.apply_url == Job_Post.apply_url),
        )
    )).scalar_one()
    # The backlog: a worker that stopped leaves its tasks pending, which no finished read shows.
    tasks = (await db.execute(
        select(
            func.count().filter(T.status == "pending").label("pending"),
            func.count().filter(T.status == "claimed").label("claimed"),
            func.min(T.created_at).filter(T.status == "pending").label("oldest_pending_at"),
        )
    )).one()
    return {**row._asdict(), **tasks._asdict(), "open_jobs": open_jobs}


async def systems(db: AsyncSession) -> list[dict]:
    '''enabled boards by hiring system, most boards first: how many the catalog holds, how many were
    ever read, and the newest read'''
    rows = (await db.execute(
        select(
            S.ats, func.count().label("boards"), func.count(S.last_read_at).label("read"),
            func.max(S.last_read_at).label("last_read_at"),
        ).where(S.enabled.is_(True)).group_by(S.ats).order_by(func.count().desc(), S.ats)
    )).all()
    return [r._asdict() for r in rows]


async def daily_reads(db: AsyncSession, *, days: int) -> list[dict]:
    '''the last `days` days by day (UTC) and hiring system, newest day first: board reads done and
    failed, their mean seconds from start to finish, and the jobs first seen on its boards'''
    since = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=days)
    task_day = func.date(func.timezone("UTC", T.finished_at)).label("day")
    reads = (await db.execute(
        select(
            task_day, S.ats,
            func.count().filter(T.status == "done").label("done"),
            func.count().filter(T.status == "failed").label("failed"),
            func.avg(func.extract("epoch", T.finished_at - T.started_at))
            .filter(T.status == "done").label("mean_seconds"),
        ).join(S, S.id == T.schedule_id)
        .where(T.finished_at >= since).group_by(task_day, S.ats)
    )).all()
    seen_day = func.date(func.timezone("UTC", J.first_seen_at)).label("day")
    new = (await db.execute(
        select(seen_day, S.ats, func.count(J.apply_url.distinct()).label("new_jobs"))
        .join(S, S.id == J.schedule_id)
        .where(J.first_seen_at >= since).group_by(seen_day, S.ats)
    )).all()
    rows: dict[tuple, dict] = {}
    for r in reads:
        rows[(r.day, r.ats)] = {
            "done": r.done, "failed": r.failed,
            "mean_seconds": float(r.mean_seconds) if r.mean_seconds is not None else None,
        }
    for r in new:
        rows.setdefault((r.day, r.ats), {"done": 0, "failed": 0, "mean_seconds": None})["new_jobs"] = r.new_jobs
    return [
        {"day": day.isoformat(), "ats": ats, "new_jobs": 0, **counts}
        for (day, ats), counts in sorted(rows.items(), key=lambda kv: (-kv[0][0].toordinal(), kv[0][1]))
    ]


async def failing_boards(db: AsyncSession) -> list[dict]:
    '''enabled boards whose last reads failed, most failures first, each with its latest failed read's error'''
    last_error = (
        select(T.error).where(T.schedule_id == S.id, T.status == "failed")
        .order_by(T.finished_at.desc()).limit(1).scalar_subquery()
    )
    rows = (await db.execute(
        select(S.ats, S.token, S.company, S.consecutive_failures, S.last_read_at, S.rest_until,
               last_error.label("last_error"))
        .where(S.enabled.is_(True), S.consecutive_failures > 0)
        .order_by(S.consecutive_failures.desc(), S.company).limit(FAILING_LIMIT)
    )).all()
    return [r._asdict() for r in rows]


# ponytail: kept per process, so each API instance reads once per KEEP_SECONDS; a shared store if that is too many.
_kept: dict[int, tuple[float, dict]] = {}


def forget() -> None:
    '''drops the kept answers (tests)'''
    _kept.clear()


async def scrape_health(db: AsyncSession, *, days: int) -> dict:
    '''the whole answer for `days`, kept for KEEP_SECONDS so many opens cost one read; `read_at` says when
    it was read, and `last_import_at` is the newest job posting write, the scheduled feed import's trace'''
    kept = _kept.get(days)
    if kept and time.monotonic() - kept[0] < KEEP_SECONDS:
        return kept[1]
    answer = {
        "read_at": datetime.datetime.now(datetime.UTC),
        "last_import_at": (await db.execute(select(func.max(Job_Post.updated_at)))).scalar_one(),
        "boards": await boards_summary(db),
        "systems": await systems(db),
        "days": await daily_reads(db, days=days),
        "failing": await failing_boards(db),
    }
    _kept[days] = (time.monotonic(), answer)
    return answer
