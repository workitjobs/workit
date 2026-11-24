"""Board catalog sync, due-schedule selection and read advancement.

Reimplements store.py's board health logic (rest_for, consecutive_failures)
in Postgres, using the same constants. Adds quiet board stagger and fingerprint
rest (KAN-722).
"""

from __future__ import annotations

import csv
import time
from pathlib import Path

from sqlalchemy import select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncConnection
from workit_scraper.scheduling import (
    FINGERPRINT_FIRST,
    FINGERPRINT_LONGEST,
    RUN_EVERY,  # noqa: F401 — re-exported for tests
    is_quiet_board_due,
    quiet_slot,
    rest_for,
)

from app.models.scraper import Scraper_Schedule

_schedules = Scraper_Schedule.__table__

BOARDS_CSV = Path(__file__).resolve().parents[3] / "scraper" / "boards.csv"
# Boards per catalog upsert: 8,000 bind parameters, well under asyncpg's 32,767.
SYNC_BATCH = 1000


def filter_quiet(schedules: list, *, full: bool = False) -> list:
    """Drop quiet boards not due this slot. Pure function on rows.

    A board is kept if any of: full mode, never read, has_kept (hot),
    last read > QUIET_LONGEST ago, or its CRC32 slot matches this run's slot.
    """
    if full:
        return list(schedules)
    now = time.time()
    slot = quiet_slot(now)
    return [
        row
        for row in schedules
        if is_quiet_board_due(
            f"{row.ats}/{row.token}",
            slot,
            row.last_read_at.timestamp() if row.last_read_at else None,
            now,
            has_kept=row.has_kept,
        )
    ]


async def sync_catalog(conn: AsyncConnection, boards_csv: Path = BOARDS_CSV) -> int:
    """Upsert boards.csv into scraper_schedules. Returns count of new rows."""
    boards = _load_csv(boards_csv)
    new = 0
    # In batches, in the caller's one transaction: asyncpg takes 32,767 bind
    # parameters a statement and a board is 8, so one INSERT of the whole
    # catalog failed past 4,095 boards and no cycle could start (2026-11-23).
    for start in range(0, len(boards), SYNC_BATCH):
        stmt = insert(_schedules).values(boards[start : start + SYNC_BATCH])
        stmt = stmt.on_conflict_do_update(
            index_elements=[_schedules.c.ats, _schedules.c.token],
            set_={"company": stmt.excluded.company},
        ).returning(text("xmax = 0"))
        new += sum(1 for row in await conn.execute(stmt) if row[0])
    return new


async def select_due(conn: AsyncConnection, *, full: bool = False) -> list:
    """Schedules due for a read: enabled, not health-resting, not fingerprint-resting."""
    stmt = select(_schedules).where(
        _schedules.c.enabled.is_(True),
        _schedules.c.rest_until.is_(None) | (_schedules.c.rest_until <= text("now()")),
    )
    if not full:
        stmt = stmt.where(
            _schedules.c.fingerprint_until.is_(None)
            | (_schedules.c.fingerprint_until <= text("now()"))
        )
    rows = (await conn.execute(stmt)).all()
    return filter_quiet(rows, full=full)


async def advance_reads(
    conn: AsyncConnection, schedule_id, *, now_expr=text("now()")
) -> None:
    """After a complete board read: move last_read_at to prior_read_at, so the
    last two complete reads are kept, then advance last_read_at and clear
    failures and rest."""
    await conn.execute(
        update(_schedules)
        .where(_schedules.c.id == schedule_id)
        .values(
            # The old value: SET reads every column as it was before the UPDATE.
            prior_read_at=_schedules.c.last_read_at,
            last_read_at=now_expr,
            missing_at=None,
            consecutive_failures=0,
            rest_until=None,
        )
    )


async def advance_fingerprint(
    conn: AsyncConnection, schedule_id, *, new_fingerprint: str
) -> None:
    """Update fingerprint state after a hot board read. Single UPDATE, no prior read.

    Sets has_kept sticky to True. If the fingerprint is unchanged, increments
    unchanged_reads and sets fingerprint_until. If changed, resets both.
    The CASE reads unchanged_reads before the UPDATE sets the new value,
    so the exponent is the pre-increment count.
    """
    await conn.execute(
        update(_schedules)
        .where(_schedules.c.id == schedule_id)
        .values(
            fingerprint=new_fingerprint,
            has_kept=text("true"),
            unchanged_reads=text(
                "CASE WHEN fingerprint = :fp"
                " THEN unchanged_reads + 1 ELSE 0 END"
            ),
            fingerprint_until=text(
                "CASE WHEN fingerprint = :fp AND has_kept"
                " THEN now() + make_interval("
                "   secs => LEAST("
                f"     {int(FINGERPRINT_FIRST.total_seconds())}"
                "       * pow(2, unchanged_reads),"
                f"     {int(FINGERPRINT_LONGEST.total_seconds())}"
                "   ))"
                " ELSE NULL END"
            ),
        ),
        {"fp": new_fingerprint},
    )


async def record_missing(conn: AsyncConnection, schedule_id) -> None:
    """A board said 'no such board'. First time: note it. Second: treat as a
    complete read with nothing open (same logic as store.update)."""
    row = (
        await conn.execute(
            select(_schedules.c.missing_at, _schedules.c.last_read_at).where(
                _schedules.c.id == schedule_id
            )
        )
    ).one()
    if row.missing_at is None:
        await conn.execute(
            update(_schedules)
            .where(_schedules.c.id == schedule_id)
            .values(missing_at=text("now()"))
        )
    else:
        # Second miss: count as complete read with nothing listed.
        # Clear failures, rest and fingerprint state.
        await conn.execute(
            update(_schedules)
            .where(_schedules.c.id == schedule_id)
            .values(
                prior_read_at=_schedules.c.missing_at,
                last_read_at=text("now()"),
                missing_at=None,
                consecutive_failures=0,
                rest_until=None,
                fingerprint=None,
                unchanged_reads=0,
                fingerprint_until=None,
            )
        )


async def record_failure(conn: AsyncConnection, schedule_id) -> None:
    """Increment consecutive_failures and set rest_until if past threshold."""
    row = (
        await conn.execute(
            select(_schedules.c.consecutive_failures).where(
                _schedules.c.id == schedule_id
            )
        )
    ).one()
    new_failures = row.consecutive_failures + 1
    rest = rest_for(new_failures)
    await conn.execute(
        update(_schedules)
        .where(_schedules.c.id == schedule_id)
        .values(
            consecutive_failures=new_failures,
            rest_until=text("now() + make_interval(secs => :rest_secs)")
            if rest
            else None,
        ),
        {"rest_secs": rest.total_seconds()} if rest else {},
    )


def _load_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = csv.DictReader(line for line in f if not line.startswith("#"))
        result = []
        for row in rows:
            ats = (row.get("ats") or "").strip()
            token = (row.get("token") or "").strip()
            if ats and token:
                result.append(
                    {
                        "ats": ats,
                        "token": token,
                        "company": (row.get("company") or token).strip(),
                    }
                )
        return result
