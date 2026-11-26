"""Per-board work items with lease-based claiming.

Creates one task per due schedule, claims with FOR UPDATE SKIP LOCKED so
concurrent workers never double-read a board, and marks done/failed after.
"""

from __future__ import annotations

import re
from datetime import timedelta

from sqlalchemy import text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncConnection

from app.models.scraper import Scraper_Task

_tasks = Scraper_Task.__table__

LEASE_DURATION = timedelta(minutes=30)

# Matches key=value pairs where the key looks like a credential.
# Longest alternatives first so access_token wins over bare token.
_CREDENTIAL_RE = re.compile(
    r"(access_token|refresh_token|api_key|authorization|password|secret|token)"
    r"[=:]\s*[^\s&]+",
    re.IGNORECASE,
)


def _sanitize_error(error: str) -> str:
    """Strip credential-like values from an error string, then truncate."""
    cleaned = _CREDENTIAL_RE.sub(lambda m: m.group(1) + "=***", error)
    return cleaned[:2000]


async def create_tasks(conn: AsyncConnection, schedule_ids: list) -> int:
    """Insert one pending task per schedule id. Returns count inserted.

    Uses ON CONFLICT DO NOTHING against the partial unique index on
    (schedule_id) WHERE status IN ('pending', 'claimed'), so two concurrent
    runs race harmlessly: the second's duplicates are silently skipped by
    Postgres instead of the check-then-insert that the first design used.
    """
    if not schedule_ids:
        return 0
    stmt = insert(_tasks).values([{"schedule_id": sid} for sid in schedule_ids])
    stmt = stmt.on_conflict_do_nothing(
        index_elements=[_tasks.c.schedule_id],
        index_where=_tasks.c.status.in_(["pending", "claimed"]),
    )
    result = await conn.execute(stmt)
    return result.rowcount


async def claim_task(conn: AsyncConnection, worker_id: str) -> object | None:
    """Claim one pending task with FOR UPDATE SKIP LOCKED. Returns the row or None."""
    # Raw SQL: SQLAlchemy Core doesn't expose SKIP LOCKED on UPDATE ... RETURNING.
    result = await conn.execute(
        text("""
            UPDATE scraper_tasks
            SET status = 'claimed',
                claimed_by = :worker,
                claimed_at = now(),
                lease_expires_at = now() + :lease
            WHERE id = (
                SELECT id FROM scraper_tasks
                WHERE status = 'pending'
                ORDER BY created_at
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            RETURNING *
        """),
        {
            "worker": worker_id,
            "lease": LEASE_DURATION,
        },
    )
    return result.first()


async def mark_started(conn: AsyncConnection, task_id) -> None:
    """Record when the actual scrape began."""
    await conn.execute(
        update(_tasks).where(_tasks.c.id == task_id).values(started_at=text("now()"))
    )


async def mark_done(
    conn: AsyncConnection,
    task_id,
    *,
    boards_s: float | None = None,
    pages_s: float | None = None,
) -> None:
    """Mark a task as successfully completed."""
    await conn.execute(
        update(_tasks)
        .where(_tasks.c.id == task_id)
        .values(
            status="done",
            finished_at=text("now()"),
            boards_s=boards_s,
            pages_s=pages_s,
        )
    )


async def mark_failed(
    conn: AsyncConnection, task_id, *, error: str | None = None
) -> None:
    """Mark a task as failed."""
    await conn.execute(
        update(_tasks)
        .where(_tasks.c.id == task_id)
        .values(
            status="failed",
            finished_at=text("now()"),
            error=_sanitize_error(error) if error else None,
        )
    )


async def expire_leases(conn: AsyncConnection) -> int:
    """Reset stale claimed tasks back to pending. Returns count expired."""
    result = await conn.execute(
        update(_tasks)
        .where(
            _tasks.c.status == "claimed",
            _tasks.c.lease_expires_at <= text("now()"),
        )
        .values(
            status="pending",
            claimed_by=None,
            claimed_at=None,
            lease_expires_at=None,
        )
    )
    return result.rowcount


async def bulk_log_tasks(conn: AsyncConnection, results: list[dict]) -> int:
    """Insert one task-log row per board result in a single statement (D4).

    Each dict must have schedule_id, status ('done' or 'failed'), started_at,
    finished_at, and optionally boards_s, pages_s, error. Error strings are
    sanitized through _sanitize_error (H3).

    Returns the count of rows inserted.
    """
    if not results:
        return 0
    rows = []
    for r in results:
        row = {
            "schedule_id": r["schedule_id"],
            "status": r["status"],
            "started_at": r["started_at"],
            "finished_at": r["finished_at"],
        }
        if r.get("boards_s") is not None:
            row["boards_s"] = r["boards_s"]
        if r.get("pages_s") is not None:
            row["pages_s"] = r["pages_s"]
        if r.get("error"):
            row["error"] = _sanitize_error(r["error"])
        rows.append(row)
    result = await conn.execute(insert(_tasks).values(rows))
    return result.rowcount
