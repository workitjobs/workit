"""Board catalog sync, due-schedule selection and read advancement.

Reimplements store.py's board health logic (rest_for, consecutive_failures)
in Postgres, using the same constants. Adds quiet board stagger and fingerprint
rest (KAN-722).
"""

from __future__ import annotations

import csv
import datetime
import time
import uuid
from datetime import timedelta
from pathlib import Path

from sqlalchemy import func, select, text, update
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

CYCLE_LEASE_DURATION = timedelta(minutes=30)

BOARDS_CSV = Path(__file__).resolve().parents[3] / "scraper" / "boards.csv"
# Boards per catalog upsert: 8,000 bind parameters, well under asyncpg's 32,767.
SYNC_BATCH = 1000


def filter_quiet(
    schedules: list, *, full: bool = False, now: float | None = None
) -> list:
    """Drop quiet boards not due this slot. Pure function on rows.

    A board is kept if any of: full mode, never read, has_kept (hot),
    last read > QUIET_LONGEST ago, or its CRC32 slot matches this run's slot.

    When *now* (a Unix timestamp) is given, use it instead of time.time(),
    so the caller can pass the database clock (H4: clock consistency).
    """
    if full:
        return list(schedules)
    if now is None:
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
    if not boards:
        return 0
    new = 0
    # In batches, in the caller's one transaction: asyncpg takes 32,767 bind
    # parameters a statement and a board is 8, so one INSERT of the whole
    # catalog failed past 4,095 boards and no cycle could start (2026-11-23).
    for start in range(0, len(boards), SYNC_BATCH):
        stmt = insert(_schedules).values(boards[start : start + SYNC_BATCH])
        stmt = stmt.on_conflict_do_update(
            index_elements=[_schedules.c.ats, _schedules.c.token],
            set_={"company": stmt.excluded.company},
            where=_schedules.c.company.is_distinct_from(stmt.excluded.company),
        ).returning(text("xmax = 0"))
        new += sum(1 for row in await conn.execute(stmt) if row[0])
    return new


async def sync_catalog_diff(
    conn: AsyncConnection, boards_csv: Path | None = None
) -> tuple[list, int, datetime.datetime]:
    """Read all schedules with db_now, diff with boards.csv, write only changes.

    Returns (all_rows, new_count, db_now). Usually 0 writes between deploys.
    The db_now comes from the same SELECT as the rows, so Python-side due
    checks use the database clock (H4).

    *boards_csv* defaults to the module-level ``BOARDS_CSV`` at call time
    (not definition time), so a monkeypatch on the module attribute works.
    """
    if boards_csv is None:
        boards_csv = BOARDS_CSV
    result = await conn.execute(
        select(*_schedules.c, func.now().label("db_now"))
    )
    existing = result.all()

    if existing:
        db_now = existing[0].db_now
    else:
        db_now = (await conn.execute(text("SELECT now()"))).scalar()

    csv_boards = _load_csv(boards_csv)
    if not csv_boards:
        return existing, 0, db_now

    by_key = {(r.ats, r.token): r for r in existing}
    to_insert = []
    to_update = []
    for board in csv_boards:
        key = (board["ats"], board["token"])
        row = by_key.get(key)
        if row is None:
            to_insert.append(board)
        elif row.company != board["company"]:
            to_update.append((row.id, board["company"]))

    new_rows: list = []
    if to_insert:
        # Batch inserts to stay under asyncpg's 32 767 parameter limit.
        # Each row binds ~8 params (3 from the dict + Python-side defaults).
        batch_size = 32_767 // 10  # generous headroom
        for i in range(0, len(to_insert), batch_size):
            chunk = to_insert[i : i + batch_size]
            stmt = insert(_schedules).values(chunk).returning(*_schedules.c)
            new_rows.extend((await conn.execute(stmt)).all())

    if to_update:
        for schedule_id, company in to_update:
            await conn.execute(
                update(_schedules)
                .where(_schedules.c.id == schedule_id)
                .values(company=company)
            )

    all_rows = list(existing) + new_rows
    return all_rows, len(new_rows), db_now


def select_due_from_rows(
    rows: list, db_now: datetime.datetime, *, full: bool = False
) -> list:
    """Due schedules computed in Python from the rows read by sync_catalog_diff.

    Checks enabled, rest_until, fingerprint_until, then filter_quiet with
    the database clock (H4).
    """
    now_ts = db_now.timestamp()
    due = [
        row
        for row in rows
        if row.enabled
        and (row.rest_until is None or row.rest_until <= db_now)
        and (full or row.fingerprint_until is None or row.fingerprint_until <= db_now)
    ]
    return filter_quiet(due, full=full, now=now_ts)


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


async def take_lease(
    conn: AsyncConnection,
    holder: str,
    duration: timedelta = CYCLE_LEASE_DURATION,
) -> uuid.UUID | None:
    """Try to take the cycle lease (D5). Returns the lease id, or None if held.

    The seeded row's expires_at is epoch, so the first cycle takes it.
    A second process whose take returns None exits without writing.
    """
    result = await conn.execute(
        text(
            "UPDATE scraper_cycle_leases"
            " SET holder = :holder,"
            "     expires_at = now() + :duration,"
            "     started_at = now()"
            " WHERE expires_at < now()"
            " RETURNING id"
        ),
        {"holder": holder, "duration": duration},
    )
    row = result.first()
    return row.id if row else None


async def renew_lease(
    conn: AsyncConnection,
    lease_id: uuid.UUID,
    holder: str,
    duration: timedelta = CYCLE_LEASE_DURATION,
) -> bool:
    """Renew the cycle lease. Returns False if another holder took it (H2).

    Called inside each batch transaction. The writer aborts if this returns
    False, since another process has taken the lease.
    """
    result = await conn.execute(
        text(
            "UPDATE scraper_cycle_leases"
            " SET expires_at = now() + :duration"
            " WHERE id = :lid AND holder = :holder"
        ),
        {"lid": lease_id, "holder": holder, "duration": duration},
    )
    return result.rowcount > 0


async def release_lease(
    conn: AsyncConnection, lease_id: uuid.UUID, holder: str
) -> None:
    """Release the cycle lease so the next cycle can take it."""
    await conn.execute(
        text(
            "UPDATE scraper_cycle_leases"
            " SET holder = NULL,"
            "     expires_at = '1970-01-01 00:00:00+00'"
            " WHERE id = :lid AND holder = :holder"
        ),
        {"lid": lease_id, "holder": holder},
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
