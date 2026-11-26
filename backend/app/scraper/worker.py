"""Orchestrate one scrape cycle: sync catalog, read boards and batch-write
results, enrich descriptions and close stale jobs.

Architecture (plan rev 2):
- 4 async reader tasks pull boards from an asyncio.Queue, read them over the
  network via to_thread, compare fingerprints in memory and put results on a
  results queue.  No database access.
- 1 writer task collects results, batches them (BATCH_BOARDS or BATCH_SECONDS)
  and writes each batch in one transaction: import_feed for changed boards,
  update_sources, bulk schedule updates and a task-log INSERT.
- A cycle lease (D5) prevents two workers from running at the same time.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import datetime
import logging
import time
import uuid
from dataclasses import dataclass, field

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine
from workit_scraper import providers
from workit_scraper.board_read import BoardRead, ReadStatus, read_board
from workit_scraper.polite import Robots
from workit_scraper.providers import PROVIDERS, Board, Job
from workit_scraper.scheduling import fingerprint as compute_fingerprint
from workit_scraper.shortlist import classify

from app.models.job_roles import Job_Role
from app.models.locations import Country, State
from app.schemas.jobs import JobListing
from app.scraper.closures import (
    detect_and_close,
    update_sources,
)
from app.scraper.schedules import (
    advance_fingerprint,
    advance_reads,
    record_failure,
    record_missing,
    release_lease,
    renew_lease,
    select_due_from_rows,
    sync_catalog_diff,
    take_lease,
)
from app.scraper.tasks import bulk_log_tasks
from app.services.location_resolver import LocationResolver
from app.services.role_resolver import RoleResolver

logger = logging.getLogger(__name__)

# Same work_style mapping as feed.py.
_WORK_STYLE = {"Remote": "remote", "Hybrid": "hybrid", "On site": "onsite"}

# A board returning more listings than this is treated as failed.
MAX_BOARD_LISTINGS = 5000

# Phase 2: description enrichment.
MAX_DESCRIPTIONS_PER_CYCLE = 500
DESCRIPTION_BATCH_SIZE = 50
DESCRIPTION_WORKERS = 8
BOARD_WORKERS = 4
MAX_DESCRIPTION_ATTEMPTS = 3

# Batch writer (D7).
BATCH_BOARDS = 50
BATCH_SECONDS = 60

# Sentinel value placed on the results queue after all readers finish.
_SENTINEL = object()


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Read:
    """One board's read result, produced by a reader and consumed by the writer."""

    schedule: object  # the schedule row from the initial SELECT
    status: str  # "done", "failed", or "missing"
    listings: list[JobListing] = field(default_factory=list)
    all_postings: list[tuple[str, str]] = field(default_factory=list)
    inline_urls: list[str] = field(default_factory=list)
    boards_s: float = 0.0
    fingerprint: str | None = None
    unchanged: bool = False
    error: str | None = None
    started_at: datetime.datetime | None = None
    finished_at: datetime.datetime | None = None


# ---------------------------------------------------------------------------
# Pure helpers (preserved from the old worker)
# ---------------------------------------------------------------------------


def read_board_listing(board: Board, robots: Robots | None = None) -> tuple[BoardRead, list[Job], float]:
    """Read one board's listing and filter by title only (phase 1).

    Descriptions are fetched separately in phase 2.  Blocking: run in a
    thread.  Returns ``(result, kept_jobs, boards_s)``."""
    if robots is None:
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


# ---------------------------------------------------------------------------
# Reader (network only, no database)
# ---------------------------------------------------------------------------


async def _reader(
    queue: asyncio.Queue,
    results: asyncio.Queue,
    robots: Robots,
) -> None:
    """Take boards from *queue*, read them over the network, put _Read results
    on *results*.  Runs until it gets None from the queue (sentinel)."""
    while True:
        schedule = await queue.get()
        if schedule is None:
            break

        started_at = datetime.datetime.now(tz=datetime.UTC)
        provider = PROVIDERS.get(schedule.ats)
        if provider is None:
            results.put_nowait(_Read(
                schedule=schedule,
                status="failed",
                error=f"unknown provider: {schedule.ats}",
                started_at=started_at,
                finished_at=datetime.datetime.now(tz=datetime.UTC),
            ))
            continue

        board = Board(schedule.ats, schedule.token, schedule.company)
        try:
            result, jobs, boards_s = await asyncio.to_thread(
                read_board_listing, board, robots
            )
        except Exception as exc:
            results.put_nowait(_Read(
                schedule=schedule,
                status="failed",
                error=str(exc)[:200],
                boards_s=0.0,
                started_at=started_at,
                finished_at=datetime.datetime.now(tz=datetime.UTC),
            ))
            continue

        finished_at = datetime.datetime.now(tz=datetime.UTC)

        if result.status is ReadStatus.MISSING:
            logger.info("Board %s/%s: not found", schedule.ats, schedule.token)
            results.put_nowait(_Read(
                schedule=schedule,
                status="missing",
                boards_s=boards_s,
                started_at=started_at,
                finished_at=finished_at,
            ))
            continue

        if result.status is not ReadStatus.OK:
            error = f"{result.reason}: {result.error}" if result.error else result.reason
            logger.warning(
                "Board %s/%s unread: %s", schedule.ats, schedule.token, error
            )
            results.put_nowait(_Read(
                schedule=schedule,
                status="failed",
                error=error,
                boards_s=boards_s,
                started_at=started_at,
                finished_at=finished_at,
            ))
            continue

        # Oversized board guard.
        listings = [job_to_listing(job, schedule.company) for job in jobs]
        if len(listings) > MAX_BOARD_LISTINGS:
            error = f"oversized: {len(listings)} listings (max {MAX_BOARD_LISTINGS})"
            logger.warning("Board %s/%s: %s", schedule.ats, schedule.token, error)
            results.put_nowait(_Read(
                schedule=schedule,
                status="failed",
                error=error,
                boards_s=boards_s,
                started_at=started_at,
                finished_at=finished_at,
            ))
            continue

        # Compute fingerprint for hot boards (D1).
        has_kept = bool(jobs)
        if has_kept or schedule.has_kept:
            fp = compute_fingerprint(job.external_id for job in jobs)
        else:
            fp = None

        # Compare fingerprint to decide unchanged (D2, D8).
        unchanged = (
            fp is not None
            and schedule.fingerprint is not None
            and fp == schedule.fingerprint
        )

        inline_urls = [
            job.apply_url
            for job in jobs
            if job.page and job.page.version == providers.PAGE_VERSION
        ]

        all_postings = [(job.apply_url, job.external_id) for job in result.jobs]

        logger.info(
            "Board %s/%s: %d of %d postings kept (%d inline), %.1fs%s",
            schedule.ats,
            schedule.token,
            len(jobs),
            len(result.jobs),
            len(inline_urls),
            boards_s,
            " [unchanged]" if unchanged else "",
        )

        results.put_nowait(_Read(
            schedule=schedule,
            status="done",
            listings=[] if unchanged else listings,
            all_postings=[] if unchanged else all_postings,
            inline_urls=[] if unchanged else inline_urls,
            boards_s=boards_s,
            fingerprint=fp,
            unchanged=unchanged,
            started_at=started_at,
            finished_at=finished_at,
        ))


# ---------------------------------------------------------------------------
# Writer (single connection, batch transactions)
# ---------------------------------------------------------------------------


async def _write_batch(
    conn: AsyncConnection,
    batch: list[_Read],
    summary: dict,
    *,
    resolver: LocationResolver,
    role_resolver: RoleResolver,
    lease_id: uuid.UUID,
    holder: str,
) -> bool:
    """Write one batch of board results in a single transaction (D7).

    Returns True on success, False if the lease was lost (H2) or the
    transaction failed."""
    try:
        # 1. import_feed for changed boards only (D2).
        changed = [r for r in batch if r.status == "done" and not r.unchanged]
        if changed:
            all_listings: list[JobListing] = []
            for r in changed:
                all_listings.extend(r.listings)

            if all_listings:
                # Deduplicate by apply_url (H6): keep the listing with more data
                # (description_version set > unset, i.e. has description).
                seen: dict[str, JobListing] = {}
                for listing in all_listings:
                    existing = seen.get(listing.apply_url)
                    if existing is None or listing.description and not existing.description:
                        seen[listing.apply_url] = listing
                all_listings = list(seen.values())

                from app.scripts.import_jobs import import_feed

                await import_feed(
                    conn,
                    all_listings,
                    close_missing=False,
                    resolver=resolver,
                    role_resolver=role_resolver,
                )

        # 2. update_sources for changed boards only (D2).
        for r in changed:
            if r.all_postings:
                await update_sources(
                    conn,
                    r.schedule.id,
                    r.all_postings,
                    inline_versions={
                        url: providers.PAGE_VERSION for url in r.inline_urls
                    },
                )

        # 3. Bulk schedule updates.
        for r in batch:
            if r.status == "done":
                # advance_reads for ALL done boards, changed and unchanged (D2).
                await advance_reads(conn, r.schedule.id)
                if r.fingerprint is not None:
                    await advance_fingerprint(
                        conn, r.schedule.id, new_fingerprint=r.fingerprint
                    )
                summary["boards_ok"] += 1
                summary["jobs_scraped"] += len(r.listings)
            elif r.status == "missing":
                await record_missing(conn, r.schedule.id)
                summary["boards_missing"] += 1
            elif r.status == "failed":
                await record_failure(conn, r.schedule.id)
                summary["boards_failed"] += 1

        # 4. Bulk task log INSERT (D4, H3).
        task_rows = []
        for r in batch:
            task_rows.append({
                "schedule_id": r.schedule.id,
                "status": "done" if r.status in ("done", "missing") else "failed",
                "started_at": r.started_at,
                "finished_at": r.finished_at,
                "boards_s": r.boards_s if r.boards_s else None,
                "error": r.error,
            })
        await bulk_log_tasks(conn, task_rows)

        # 5. Renew cycle lease (H2).
        if not await renew_lease(conn, lease_id, holder):
            logger.error("Lease lost: another process took it; aborting batch")
            await conn.rollback()
            return False

        # 6. Commit.
        await conn.commit()
        return True

    except Exception:
        logger.exception("Batch write failed for %d boards", len(batch))
        try:
            await conn.rollback()
        except Exception:
            logger.exception("Rollback also failed")
        # Count the boards as failed in summary.
        for r in batch:
            if r.status == "done":
                summary["boards_failed"] += 1
                summary["boards_ok"] -= 1  # undo the count from above
                summary["jobs_scraped"] -= len(r.listings)
            elif r.status == "missing":
                summary["boards_failed"] += 1
                summary["boards_missing"] -= 1
        return False


async def _writer(
    conn: AsyncConnection,
    results: asyncio.Queue,
    summary: dict,
    *,
    resolver: LocationResolver,
    role_resolver: RoleResolver,
    lease_id: uuid.UUID,
    holder: str,
) -> None:
    """Collect reader results, batch them and write each batch (D7).

    Batches when BATCH_BOARDS results are collected or BATCH_SECONDS have
    elapsed since the batch started, whichever comes first."""
    batch: list[_Read] = []
    batch_start = time.monotonic()

    async def flush() -> bool:
        nonlocal batch, batch_start
        if not batch:
            return True
        ok = await _write_batch(
            conn,
            batch,
            summary,
            resolver=resolver,
            role_resolver=role_resolver,
            lease_id=lease_id,
            holder=holder,
        )
        batch = []
        batch_start = time.monotonic()
        return ok

    while True:
        # Wait for the next result, with a timeout so we flush partial batches.
        remaining = max(0.1, BATCH_SECONDS - (time.monotonic() - batch_start))
        try:
            item = await asyncio.wait_for(results.get(), timeout=remaining)
        except TimeoutError:
            # Timeout: flush the partial batch.
            if not await flush():
                # Lease lost: drain and discard remaining results.
                break
            continue

        if item is _SENTINEL:
            break

        batch.append(item)

        if len(batch) >= BATCH_BOARDS and not await flush():
            break

    # Final flush (the last partial batch).
    await flush()


# ---------------------------------------------------------------------------
# Resolver construction (D9)
# ---------------------------------------------------------------------------


async def _build_resolvers(
    conn: AsyncConnection,
) -> tuple[LocationResolver, RoleResolver]:
    """Build LocationResolver and RoleResolver once per cycle (D9)."""
    countries = set((await conn.scalars(select(Country.code))).all())
    states = {
        row.code: row.name
        for row in await conn.execute(select(State.code, State.name))
    }
    resolver = await asyncio.to_thread(LocationResolver, countries, states)

    job_roles = {
        row.slug: row.name
        for row in await conn.execute(select(Job_Role.slug, Job_Role.name))
    }
    role_resolver = RoleResolver(job_roles)

    return resolver, role_resolver


# ---------------------------------------------------------------------------
# Main cycle
# ---------------------------------------------------------------------------


async def run_cycle(
    engine: AsyncEngine,
    *,
    dry_run: bool = False,
    full: bool = False,
    workers: int = BOARD_WORKERS,
) -> dict:
    """One full worker cycle.  Returns a summary dict.

    Takes an *engine* (not a connection) because readers use no database and
    the writer opens its own connection."""
    if workers < 1:
        raise ValueError(f"workers must be >= 1, got {workers}")

    holder = f"worker-{uuid.uuid4().hex[:8]}"
    summary: dict = {
        "worker": holder,
        "synced": 0,
        "boards_ok": 0,
        "boards_unchanged": 0,
        "boards_missing": 0,
        "boards_failed": 0,
        "boards_changed": 0,
        "jobs_scraped": 0,
        "descriptions_fetched": 0,
        "descriptions_failed": 0,
        "jobs_closed": 0,
        "dry_run": dry_run,
    }

    async with engine.connect() as conn:
        # 1. Catalog diff + schedule read + db_now (D6, H4).
        all_rows, new_count, db_now = await sync_catalog_diff(conn)
        summary["synced"] = new_count

        # 2. Take cycle lease (D5).
        lease_id = await take_lease(conn, holder)
        if lease_id is None:
            logger.warning("Another cycle is running; exiting")
            await conn.rollback()
            summary["lease_held"] = True
            return summary
        await conn.commit()

        # 3. Select due schedules (D6).
        due = select_due_from_rows(all_rows, db_now, full=full)

        if dry_run:
            await release_lease(conn, lease_id, holder)
            await conn.commit()
            logger.info(
                "Dry run: would process %d boards; nothing was written", len(due)
            )
            summary["due_count"] = len(due)
            return summary

        # 4. Build resolvers once (D9).
        resolver, role_resolver = await _build_resolvers(conn)
        await conn.commit()

    # 5. Read boards in parallel (D4, D8), write batches (D7).
    input_queue: asyncio.Queue = asyncio.Queue()
    results_queue: asyncio.Queue = asyncio.Queue()

    for schedule in due:
        input_queue.put_nowait(schedule)
    # Sentinel per reader so each one stops.
    for _ in range(workers):
        input_queue.put_nowait(None)

    robots = Robots()

    reader_tasks = [
        asyncio.create_task(_reader(input_queue, results_queue, robots))
        for _ in range(workers)
    ]

    async with engine.connect() as write_conn:
        writer_task = asyncio.create_task(
            _writer(
                write_conn,
                results_queue,
                summary,
                resolver=resolver,
                role_resolver=role_resolver,
                lease_id=lease_id,
                holder=holder,
            )
        )

        # Wait for all readers to finish.
        reader_results = await asyncio.gather(
            *reader_tasks, return_exceptions=True
        )

        # H1: drain the input queue for boards no reader picked up (crash).
        for exc in reader_results:
            if isinstance(exc, BaseException):
                logger.error("Reader crashed: %s", exc)

        drained = 0
        while not input_queue.empty():
            item = input_queue.get_nowait()
            if item is None:
                continue  # skip sentinels
            results_queue.put_nowait(_Read(
                schedule=item,
                status="failed",
                error="reader crashed",
                started_at=datetime.datetime.now(tz=datetime.UTC),
                finished_at=datetime.datetime.now(tz=datetime.UTC),
            ))
            drained += 1
        if drained:
            logger.warning("Drained %d unread boards as failed", drained)

        # Signal the writer that all results are in.
        results_queue.put_nowait(_SENTINEL)
        await writer_task

        # Count changed vs unchanged from the results the writer processed.
        summary["boards_changed"] = (
            summary["boards_ok"] - summary.get("boards_unchanged", 0)
        )

    # 6. Description enrichment (phase 2).
    async with engine.connect() as conn:
        try:
            await _fetch_descriptions(conn, summary, robots=robots)
        except Exception:
            await conn.rollback()
            logger.exception(
                "Description enrichment failed; continuing to closures"
            )

        # 7. Closure detection (D10: skip when no boards changed).
        if summary["boards_changed"] > 0:
            summary["jobs_closed"] = await detect_and_close(conn)
            await conn.commit()
        else:
            logger.info(
                "All %d boards unchanged; skipping closure detection (D10)",
                summary["boards_ok"],
            )

        # 8. Release cycle lease.
        try:
            await release_lease(conn, lease_id, holder)
            await conn.commit()
        except Exception:
            logger.exception("Failed to release lease; it will expire")

    return summary


# ---------------------------------------------------------------------------
# Phase 2: description enrichment (unchanged from the old worker)
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
        WHERE ((js.description_version IS NULL
                   AND js.description_attempts < :max_attempts)
               OR (js.description_version IS NOT NULL
                   AND js.description_version < :version))
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

_STAMP_SOURCE_OK = text("""\
    UPDATE job_sources
    SET description_version = :version,
        description_fetched_at = now(),
        description_attempts = 0
    WHERE apply_url = :apply_url AND schedule_id = :schedule_id
""")

_STAMP_SOURCE_FAIL = text("""\
    UPDATE job_sources
    SET description_attempts = description_attempts + 1
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


async def _fetch_descriptions(conn: AsyncConnection, summary: dict, *, robots: Robots | None = None) -> None:
    """Phase 2: fetch descriptions for postings that lack a current one.

    Queries job_sources for rows whose description_version is NULL or stale,
    ordered by schedule_id and first_seen_at.
    Fetches pages in threads, batch-commits every DESCRIPTION_BATCH_SIZE."""
    rows = (
        await conn.execute(
            _STALE_QUERY,
            {
                "version": providers.PAGE_VERSION,
                "cap": MAX_DESCRIPTIONS_PER_CYCLE,
                "max_attempts": MAX_DESCRIPTION_ATTEMPTS,
            },
        )
    ).all()

    if not rows:
        return

    logger.info("Phase 2: %d descriptions to fetch", len(rows))
    if robots is None:
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
            await conn.execute(
                _STAMP_SOURCE_OK,
                {
                    "apply_url": row.apply_url,
                    "schedule_id": row.schedule_id,
                    "version": providers.PAGE_VERSION,
                },
            )
            fetched += 1
        else:
            await conn.execute(
                _STAMP_SOURCE_FAIL,
                {
                    "apply_url": row.apply_url,
                    "schedule_id": row.schedule_id,
                },
            )
            failed += 1
            logger.warning(
                "Description fetch failed for %s: %s",
                row.apply_url,
                error or "provider returned no description page",
            )

    await conn.commit()
    return fetched, failed
