"""Pure scheduling constants and functions shared by the scraper and the backend worker.

Both sides decide which boards to read (quiet-board stagger, failure rest,
fingerprint rest) using the same math.  This module owns that math; the
scraper's ``store`` and the backend's ``schedules`` import from it.
"""

from __future__ import annotations

import zlib
from collections.abc import Iterable
from datetime import timedelta

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: A quiet board is read on one run in this many, staggered by key.
QUIET_EVERY = 3
QUIET_LONGEST = timedelta(days=1)
#: How often the scheduled run fires (every three hours).
RUN_EVERY = timedelta(hours=3)

#: A board unread this many runs in a row starts resting.
REST_AFTER = 3
REST_FIRST = timedelta(hours=6)
REST_LONGEST = timedelta(hours=24)

#: A board whose kept postings hash the same as its last read rests.
FINGERPRINT_FIRST = timedelta(hours=4)
FINGERPRINT_LONGEST = timedelta(hours=24)


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------


def fingerprint(external_ids: Iterable[str]) -> str:
    """8-char hex CRC32 of the sorted strings in *external_ids*, joined with ``\\0``."""
    joined = "\0".join(sorted(external_ids))
    return f"{zlib.crc32(joined.encode()) & 0xFFFFFFFF:08x}"


def rest_for(failures: int) -> timedelta | None:
    """How long a board unread *failures* runs in a row rests: none below
    REST_AFTER, then REST_FIRST, doubling each miss up to REST_LONGEST."""
    if failures < REST_AFTER:
        return None
    return min(REST_FIRST * 2 ** (failures - REST_AFTER), REST_LONGEST)


def fingerprint_rest(unchanged_reads: int) -> timedelta | None:
    """How long a board unchanged *unchanged_reads* times rests: none on the
    first read (nothing to compare), then FINGERPRINT_FIRST, doubling each
    unchanged read up to FINGERPRINT_LONGEST."""
    if unchanged_reads < 1:
        return None
    return min(FINGERPRINT_FIRST * 2 ** (unchanged_reads - 1), FINGERPRINT_LONGEST)


def quiet_slot(now_seconds: float) -> int:
    """The stagger slot for the current time: ``int(now // RUN_EVERY)``."""
    return int(now_seconds // RUN_EVERY.total_seconds())


def is_quiet_board_due(
    board_key: str,
    slot: int,
    last_read_ts: float | None,
    now_ts: float,
    *,
    has_kept: bool,
) -> bool:
    """Whether a board should be read this slot.

    A board is due if it has never been read, has kept postings, was last read
    more than QUIET_LONGEST ago, or its CRC32 slot matches this run's slot.
    """
    if last_read_ts is None:
        return True
    if has_kept:
        return True
    if (now_ts - last_read_ts) >= QUIET_LONGEST.total_seconds():
        return True
    return zlib.crc32(board_key.encode()) % QUIET_EVERY == slot % QUIET_EVERY
