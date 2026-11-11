"""Orchestrate one scrape cycle: sync catalog, create tasks, claim, scrape,
publish to job_postings via import_feed, update per-board source records and
close jobs gone from all boards.

Each board publishes independently right after it is scraped, so fast boards
checkpoint without waiting for slow ones and only one board's payload is in
memory at a time. After every board is done, one final transaction detects
jobs stale on every board (two-complete-read rule) and closes them.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import time
import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection
from workit_scraper import providers
from workit_scraper.board_read import BoardRead, ReadStatus, read_board
from workit_scraper.polite import Robots
from workit_scraper.providers import PROVIDERS, Board, Job
from workit_scraper.shortlist import classify

from app.schemas.jobs import JobListing
from app.scraper.closures import (
    detect_and_close,
    update_sources,
)
from app.scraper.schedules import (
    advance_reads,
    record_failure,
    record_missing,
    select_due,
    sync_catalog,
)
from app.scraper.tasks import (
    claim_task,
    create_tasks,
    expire_leases,
    mark_done,
    mark_failed,
    mark_started,
)

logger = logging.getLogger(__name__)

# Same work_style mapping as feed.py.
_WORK_STYLE = {"Remote": "remote", "Hybrid": "hybrid", "On site": "onsite"}

# A board returning more listings than this is treated as failed.
MAX_BOARD_LISTINGS = 5000

# Phase 2: description enrichment.
MAX_DESCRIPTIONS_PER_CYCLE = 500
DESCRIPTION_BATCH_SIZE = 50
DESCRIPTION_WORKERS = 8


def read_board_listing(board: Board) -> tuple[BoardRead, list[Job], float]:
    """Read one board's listing and filter by title only (phase 1).

    Descriptions are fetched separately in phase 2.  Blocking: run in a
    thread.  Returns ``(result, kept_jobs, boards_s)``."""
    robots = Robots()
    t0 = time.monotonic()
    result = read_board(board, robots)
    boards_s = time.monotonic() - t0
    if result.status is not ReadStatus.OK:
        return result, [], boards_s
    kept = [job for job in result.jobs if classify(job.title)]
    return result, kept, boards_s


def job_to_listing(job, company: str) -> JobListing:
    """Convert a provider's Job object into a JobListing for import_feed."""
    facts = job.page.facts if job.page else None
    pay = facts.pay if facts else None

    return JobListing(
        id=job.apply_url,
        title=job.title,
        company=company,
        apply_url=job.apply_url,
        experience_level=_experience_level(facts),
        work_style=_work_style(job, facts),
        location=job.location,
        location_label=None,
        posted_at=job.posted_at,
        logo_url=None,
        company_domain=None,
        description=job.page.description if job.page else None,
        job_type=_job_type(facts),
        salary=None,
        salary_min=pay.low if pay else None,
        salary_max=pay.high if pay else None,
        salary_currency=pay.currency if pay else None,
        salary_period=pay.period if pay else None,
        min_years_experience=facts.min_years if facts else None,
        start_term=facts.start_term if facts else None,
        sponsorship=facts.sponsorship if facts else None,
    )


def _experience_level(facts) -> str | None:
    if facts is None:
        return None
    jt = facts.job_type
    if jt is None:
        return None
    if jt == "internship":
        return "student"
    return "new_grad"


def _job_type(facts) -> str | None:
    if facts is None:
        return None
    return facts.job_type


def _work_style(job, facts) -> str | None:
    # The job-level work_style (from the listing, e.g. Rippling) takes priority.
    ws = job.work_style
    if ws:
        return _WORK_STYLE.get(ws)
    if facts and facts.work_style:
        return _WORK_STYLE.get(facts.work_style)
    return None


async def run_cycle(conn: AsyncConnection, *, dry_run: bool = False) -> dict:
    """One full worker cycle. Returns a summary dict."""
    worker_id = f"worker-{uuid.uuid4().hex[:8]}"
    summary = {
        "worker": worker_id,
        "synced": 0,
        "tasks_created": 0,
        "boards_ok": 0,
        "boards_missing": 0,
        "boards_failed": 0,
        "jobs_scraped": 0,
        "descriptions_fetched": 0,
        "descriptions_failed": 0,
        "jobs_closed": 0,
        "dry_run": dry_run,
    }

    # 1-3 in one transaction, which a dry run rolls back: it reports what the
    # cycle would sync and queue, and writes nothing.
    # 1. Sync boards.csv into scraper_schedules.
    summary["synced"] = await sync_catalog(conn)

    # 2. Expire any stale leases from prior crashes.
    expired = await expire_leases(conn)
    if expired:
        logger.info("Expired %d stale task leases", expired)

    # 3. Select due schedules and create tasks.
    due = await select_due(conn)
    schedule_ids = [row.id for row in due]
    summary["tasks_created"] = await create_tasks(conn, schedule_ids)

    if dry_run:
        await conn.rollback()
        logger.info("Dry run: would process %d boards; nothing was written", len(due))
        return summary
    await conn.commit()

    # 4. Claim, process and checkpoint each board independently.
    while True:
        task = await claim_task(conn, worker_id)
        await conn.commit()
        if task is None:
            break

        done = await _process_task(conn, task, summary)
        if done is not None:
            await _checkpoint_board(conn, done, summary)

    # 5. Enrich descriptions for postings that need them.
    try:
        await _fetch_descriptions(conn, summary)
    except Exception:
        await conn.rollback()
        logger.exception("Description enrichment failed; continuing to closures")

    # 6. All boards committed; detect closures globally.
    summary["jobs_closed"] = await detect_and_close(conn)
    await conn.commit()

    return summary


@dataclass(frozen=True)
class _Read:
    """A board read whole, waiting for its jobs to publish before its task is
    marked done and its schedule advanced."""

    task_id: object
    schedule_id: object
    listings: list[JobListing]
    all_postings: list[tuple[str, str]]  # (apply_url, external_id)
    inline_urls: list[str]  # postings with inline descriptions (Lever, Ashby…)
    boards_s: float


async def _checkpoint_board(conn: AsyncConnection, done: _Read, summary: dict) -> None:
    """Publish one board's listings and advance its schedule, in one commit.
    On failure, roll back this board alone and mark it failed."""
    try:
        if done.listings:
            from app.scripts.import_jobs import import_feed

            await import_feed(conn, done.listings, close_missing=False)
            logger.info(
                "Published %d listings for schedule %s",
                len(done.listings),
                done.schedule_id,
            )
        await update_sources(
            conn,
            done.schedule_id,
            done.all_postings,
            inline_versions={url: providers.PAGE_VERSION for url in done.inline_urls},
        )
        await advance_reads(conn, done.schedule_id)
        await mark_done(conn, done.task_id, boards_s=done.boards_s)
        await conn.commit()
        summary["jobs_scraped"] += len(done.listings)
    except Exception as exc:
        await conn.rollback()
        await mark_failed(conn, done.task_id, error=f"publish failed: {exc}")
        await conn.commit()
        logger.exception("Board %s checkpoint failed; continuing", done.schedule_id)
        summary["boards_failed"] += 1


async def _process_task(conn: AsyncConnection, task, summary: dict) -> _Read | None:
    """Scrape one board. A board read whole comes back as a `_Read` for
    `run_cycle` to publish and checkpoint; any other outcome is recorded here
    and comes back as None."""
    schedule = (
        await conn.execute(
            text("SELECT * FROM scraper_schedules WHERE id = :sid"),
            {"sid": task.schedule_id},
        )
    ).first()

    if schedule is None:
        await mark_failed(conn, task.id, error="schedule not found")
        await conn.commit()
        return None

    provider = PROVIDERS.get(schedule.ats)
    if provider is None:
        await mark_failed(conn, task.id, error=f"unknown provider: {schedule.ats}")
        await record_failure(conn, task.schedule_id)
        await conn.commit()
        summary["boards_failed"] += 1
        return None

    await mark_started(conn, task.id)
    await conn.commit()

    board = Board(schedule.ats, schedule.token, schedule.company)
    result, jobs, boards_s = await asyncio.to_thread(read_board_listing, board)
    if result.status is ReadStatus.MISSING:
        logger.info("Board %s/%s: not found", schedule.ats, schedule.token)
        await record_missing(conn, task.schedule_id)
        await mark_done(conn, task.id, boards_s=boards_s)
        await conn.commit()
        summary["boards_missing"] += 1
        return None
    if result.status is not ReadStatus.OK:
        # FAILED, or SKIPPED (robots.txt, too large): no complete read, which
        # is evidence of nothing, and the board rests after enough of them.
        error = f"{result.reason}: {result.error}" if result.error else result.reason
        logger.warning("Board %s/%s unread: %s", schedule.ats, schedule.token, error)
        await record_failure(conn, task.schedule_id)
        await mark_failed(conn, task.id, error=error)
        await conn.commit()
        summary["boards_failed"] += 1
        return None

    # Convert provider Jobs to JobListing objects.
    listings = [job_to_listing(job, schedule.company) for job in jobs]

    if len(listings) > MAX_BOARD_LISTINGS:
        error = f"oversized: {len(listings)} listings (max {MAX_BOARD_LISTINGS})"
        logger.warning("Board %s/%s: %s", schedule.ats, schedule.token, error)
        await record_failure(conn, task.schedule_id)
        await mark_failed(conn, task.id, error=error)
        await conn.commit()
        summary["boards_failed"] += 1
        return None

    summary["boards_ok"] += 1

    # Postings with inline descriptions (Lever, Ashby, Recruitee) already
    # have a current Page; phase 2 will skip them.
    inline_urls = [
        job.apply_url
        for job in jobs
        if job.page and job.page.version == providers.PAGE_VERSION
    ]

    logger.info(
        "Board %s/%s: %d of %d postings kept (%d inline), %.1fs",
        schedule.ats,
        schedule.token,
        len(jobs),
        len(result.jobs),
        len(inline_urls),
        boards_s,
    )

    all_postings = [(job.apply_url, job.external_id) for job in result.jobs]
    return _Read(
        task.id, task.schedule_id, listings, all_postings, inline_urls, boards_s
    )


# ---------------------------------------------------------------------------
# Phase 2: description enrichment
# ---------------------------------------------------------------------------

_STALE_QUERY = text("""\
    WITH candidates AS (
        SELECT js.apply_url, js.external_id, js.schedule_id,
               ss.ats, ss.token, ss.company,
               jp.title, jp.work_style, js.first_seen_at,
               ROW_NUMBER() OVER (
                   PARTITION BY js.apply_url
                   ORDER BY js.schedule_id, js.first_seen_at
               ) AS rn
        FROM job_sources js
        JOIN scraper_schedules ss ON js.schedule_id = ss.id
        JOIN job_postings jp ON jp.apply_url = js.apply_url
        WHERE (js.description_version IS NULL
               OR js.description_version < :version)
          AND jp.status = 'published'
          AND jp.company_id IS NULL
          AND jp.added_by_student = FALSE
    )
    SELECT apply_url, external_id, schedule_id,
           ats, token, company, title, work_style
    FROM candidates
    WHERE rn = 1
    ORDER BY schedule_id, first_seen_at
    LIMIT :cap
""")

_UPDATE_POSTING = text("""\
    UPDATE job_postings SET
        description = :description,
        embedding = CASE WHEN description IS DISTINCT FROM :description THEN NULL ELSE embedding END,
        keywords = CASE WHEN description IS DISTINCT FROM :description THEN NULL ELSE keywords END,
        keywords_hash = CASE WHEN description IS DISTINCT FROM :description THEN NULL ELSE keywords_hash END,
        job_type = :job_type,
        experience_level = :experience_level,
        work_style = COALESCE(:work_style, work_style),
        salary_min = :salary_min,
        salary_max = :salary_max,
        salary_currency = COALESCE(:salary_currency, salary_currency),
        salary_period = COALESCE(:salary_period, salary_period),
        min_years_experience = :min_years,
        start_term = :start_term,
        sponsorship = :sponsorship,
        updated_at = now()
    WHERE apply_url = :apply_url
      AND company_id IS NULL
      AND status = 'published'
""")

_STAMP_SOURCE = text("""\
    UPDATE job_sources
    SET description_version = :version,
        description_fetched_at = CASE WHEN :fetched THEN now() ELSE description_fetched_at END
    WHERE apply_url = :apply_url AND schedule_id = :schedule_id
""")


def _describe_one(row, robots: Robots) -> tuple[object, Job | None, str | None]:
    """Fetch one posting's description page.  Blocking, runs in a thread.

    Returns ``(row, described_job | None, error | None)``.  A provider with
    no ``job_url`` (inline descriptions) returns ``(row, None, None)``."""
    provider = PROVIDERS.get(row.ats)
    if not provider or not provider.job_url:
        return row, None, None
    try:
        url = providers.job_url(row.ats, row.token, row.external_id)
        if not robots.allows(url):
            return row, None, "robots"
        robots.pace(url)
        job = Job(
            ats=row.ats,
            token=row.token,
            company=row.company,
            external_id=row.external_id,
            title=row.title,
            apply_url=row.apply_url,
            work_style=next(
                (key for key, value in _WORK_STYLE.items() if value == row.work_style),
                None,
            ),
        )
        described = providers.describe(job)
        return row, described, None
    except Exception as exc:
        return row, None, str(exc)[:200]


async def _fetch_descriptions(conn: AsyncConnection, summary: dict) -> None:
    """Phase 2: fetch descriptions for postings that lack a current one.

    Queries job_sources for rows whose description_version is NULL or stale,
    ordered by schedule_id and first_seen_at.
    Fetches pages in threads, batch-commits every DESCRIPTION_BATCH_SIZE."""
    rows = (
        await conn.execute(
            _STALE_QUERY,
            {"version": providers.PAGE_VERSION, "cap": MAX_DESCRIPTIONS_PER_CYCLE},
        )
    ).all()

    if not rows:
        return

    logger.info("Phase 2: %d descriptions to fetch", len(rows))
    robots = Robots()
    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=DESCRIPTION_WORKERS) as pool:
        results = await asyncio.gather(
            *(loop.run_in_executor(pool, _describe_one, row, robots) for row in rows)
        )
    for offset in range(0, len(results), DESCRIPTION_BATCH_SIZE):
        fetched, failed = await _commit_description_batch(
            conn, results[offset : offset + DESCRIPTION_BATCH_SIZE]
        )
        summary["descriptions_fetched"] += fetched
        summary["descriptions_failed"] += failed
    logger.info(
        "Phase 2 done: %d fetched, %d failed",
        summary["descriptions_fetched"],
        summary["descriptions_failed"],
    )


async def _commit_description_batch(
    conn: AsyncConnection, batch: list[tuple]
) -> tuple[int, int]:
    """Write one batch of description results to the database and commit.
    Returns ``(fetched_count, failed_count)``."""
    fetched = 0
    failed = 0
    for row, described, error in batch:
        if described and described.page:
            # Success: update posting fields and stamp source.
            facts = described.page.facts
            pay = facts.pay if facts else None
            await conn.execute(
                _UPDATE_POSTING,
                {
                    "apply_url": row.apply_url,
                    "description": described.page.description,
                    "job_type": _job_type(facts),
                    "experience_level": _experience_level(facts),
                    "work_style": _work_style(described, facts),
                    "salary_min": pay.low if pay else None,
                    "salary_max": pay.high if pay else None,
                    "salary_currency": pay.currency if pay else None,
                    "salary_period": pay.period if pay else None,
                    "min_years": facts.min_years if facts else None,
                    "start_term": facts.start_term if facts else None,
                    "sponsorship": facts.sponsorship if facts else None,
                },
            )
            fetched += 1
        else:
            failed += 1
            logger.warning(
                "Description fetch failed for %s: %s",
                row.apply_url,
                error or "provider returned no description page",
            )
        await conn.execute(
            _STAMP_SOURCE,
            {
                "apply_url": row.apply_url,
                "schedule_id": row.schedule_id,
                "version": providers.PAGE_VERSION,
                "fetched": bool(described and described.page),
            },
        )

    await conn.commit()
    return fetched, failed
