"""
The scraper's health for admins (KAN-879), behind routers/scrape_health.py:
read only from the worker's own tables (scraper_schedules, scraper_tasks,
job_sources) and job_postings, so it needs no new table and costs the worker
nothing.
"""

import datetime
import time

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

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
    (rest_until ahead), stale (unread for STALE_AFTER or never read); and the task backlog'''
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
    # The backlog: a worker that stopped leaves its tasks pending, which no finished read shows.
    tasks = (await db.execute(
        select(
            func.count().filter(T.status == "pending").label("pending"),
            func.count().filter(T.status == "claimed").label("claimed"),
            func.min(T.created_at).filter(T.status == "pending").label("oldest_pending_at"),
        )
    )).one()
    return {**row._asdict(), **tasks._asdict()}


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
        select(S.ats, S.token, S.company, S.consecutive_failures, last_error.label("last_error"))
        .where(S.enabled.is_(True), S.consecutive_failures > 0)
        .order_by(S.consecutive_failures.desc(), S.company).limit(FAILING_LIMIT)
    )).all()
    return [r._asdict() for r in rows]


async def error_groups(db: AsyncSession, *, days: int) -> list[dict]:
    '''the last `days` days' failed reads by reason, most boards first: the boards and reads each
    reason failed, its newest time, and the newest read's board and whole error as the example.
    A failed publish raises no board's consecutive_failures (worker._checkpoint_board), so this is
    the only list that holds those boards.'''
    since = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=days)
    # The worker writes "reason: detail", and the detail holds one board's values ("oversized: 5123
    # listings"), so the whole text would make a group per board.
    # ponytail: two causes behind one reason ("publish failed") share a line and show only the newest
    # example; add the exception's class to the key when that hides a second cause.
    reason = func.left(func.split_part(func.coalesce(T.error, ""), ": ", 1), 80).label("reason")
    failed = (T.status == "failed", T.finished_at >= since)
    counts = (await db.execute(
        select(
            reason, func.count(T.schedule_id.distinct()).label("boards"), func.count().label("reads"),
            func.max(T.finished_at).label("last_at"),
        ).where(*failed).group_by(reason)
    )).all()
    examples = (await db.execute(
        select(reason, S.ats, S.token, S.company, T.error)
        .join(S, S.id == T.schedule_id).where(*failed)
        .distinct(reason).order_by(reason, T.finished_at.desc(), T.id.desc())
    )).all()
    example = {e.reason: e for e in examples}
    return [
        {**c._asdict(), "ats": example[c.reason].ats, "token": example[c.reason].token,
         "company": example[c.reason].company, "error": example[c.reason].error}
        for c in sorted(counts, key=lambda c: (-c.boards, -c.reads, c.reason))
    ]


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
        "errors": await error_groups(db, days=days),
    }
    _kept[days] = (time.monotonic(), answer)
    return answer
