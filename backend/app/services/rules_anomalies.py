"""
The admins' anomaly report over the Rules table's fetch log (KAN-772, over
KAN-756's rules_fetches and the daily cap counts): which accounts fetch like
a scraper rather than a student. An account is flagged for any of

- many_systems: RULES_ANOMALY_SYSTEMS different job systems within
  RULES_ANOMALY_SYSTEMS_MINUTES. A student opens postings; a scraper walks
  the job systems to collect every table.
- fetch_without_fill: RULES_ANOMALY_MIN_FETCHES fetches or more, and
  RULES_ANOMALY_FETCHES_PER_FILL or more per fill. Fills are the account's
  fill events (daily_counts' fill_event, since fill_events names no account),
  so a student who turned Send fill numbers off shows none: read it with the
  other flags.
- regular_timing: of RULES_ANOMALY_MIN_GAPS or more gaps between fetches,
  RULES_ANOMALY_REGULAR_SHARE lie within RULES_ANOMALY_REGULAR_TOLERANCE of
  the median gap. A person's gaps scatter; a timer's don't.
- capped: RULES_TOKEN_DAILY_CAP or RULES_FETCH_DAILY_CAP reached on
  RULES_ANOMALY_CAPPED_DAYS days or more.

A flag is a lead for an admin to read, never a block. `flag` is pure (the
tests feed it rows); `report` reads the database for it.
"""

import collections
import datetime
import itertools
import statistics
import uuid
from collections.abc import Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.queries.rules import daily_counts_since, fetches_since
from app.schemas.rules_anomalies import Flag, FlaggedAccount, RulesAnomalies
from app.services.daily_caps import Capped

Fetch = tuple[uuid.UUID, str, datetime.datetime]
Count = tuple[uuid.UUID, str, datetime.date, int]


def _most_systems(fetches: list[Fetch], minutes: int) -> int:
    """The most different job systems among one account's time-ordered fetches within any `minutes`."""
    span = datetime.timedelta(minutes=minutes)
    held: collections.Counter[str] = collections.Counter()
    most = start = 0
    for _, system, at in fetches:
        held[system] += 1
        while at - fetches[start][2] > span:
            gone = fetches[start][1]
            held[gone] -= 1
            if not held[gone]:
                del held[gone]
            start += 1
        most = max(most, len(held))
    return most


def _near_median(gaps: list[float], tolerance: float) -> tuple[int, float, float]:
    """(gaps, the share within `tolerance` of the median gap, the median gap in seconds)."""
    if not gaps:
        return 0, 0.0, 0.0
    median = statistics.median(gaps)
    return len(gaps), sum(abs(g - median) <= median * tolerance for g in gaps) / len(gaps), median


def flag(fetches: Iterable[Fetch], counts: Iterable[Count], settings: Settings) -> list[FlaggedAccount]:
    """The flagged accounts among the fetches (each account's in time order), most flags then most fetches first."""
    by_account: dict[uuid.UUID, list[Fetch]] = collections.defaultdict(list)
    for fetch in fetches:
        by_account[fetch[0]].append(fetch)
    fills: collections.Counter[uuid.UUID] = collections.Counter()
    caps = {Capped.RULES_TOKEN: settings.rules_token_daily_cap, Capped.RULES_FETCH: settings.rules_fetch_daily_cap}
    capped_days: dict[uuid.UUID, set[datetime.date]] = collections.defaultdict(set)
    for account_id, kind, day, count in counts:
        if kind == Capped.FILL_EVENT:
            fills[account_id] += count
        elif kind in caps and count >= caps[kind]:
            capped_days[account_id].add(day)

    flagged = []
    for account_id, mine in by_account.items():
        mine.sort(key=lambda f: f[2])
        flags = []
        most = _most_systems(mine, settings.rules_anomaly_systems_minutes)
        if most >= settings.rules_anomaly_systems:
            flags.append(Flag(reason="many_systems",
                              detail=f"{most} job systems within {settings.rules_anomaly_systems_minutes} minutes"))
        filled = fills[account_id]
        if len(mine) >= settings.rules_anomaly_min_fetches and len(mine) >= settings.rules_anomaly_fetches_per_fill * max(filled, 1):
            flags.append(Flag(reason="fetch_without_fill", detail=f"{len(mine)} fetches, {filled} fills"))
        gaps = [(b[2] - a[2]).total_seconds() for a, b in itertools.pairwise(mine)]
        n, share, median = _near_median(gaps, settings.rules_anomaly_regular_tolerance)
        if n >= settings.rules_anomaly_min_gaps and share >= settings.rules_anomaly_regular_share:
            flags.append(Flag(reason="regular_timing",
                              detail=f"{share:.0%} of {n} gaps within {settings.rules_anomaly_regular_tolerance:.0%} of {median:.0f} s"))
        capped = len(capped_days.get(account_id, ()))
        if capped >= settings.rules_anomaly_capped_days:
            flags.append(Flag(reason="capped", detail=f"at the daily cap on {capped} days"))
        if flags:
            flagged.append(FlaggedAccount(
                account_id=account_id, fetches=len(mine), job_systems=sorted({f[1] for f in mine}), fills=filled,
                first_fetch=mine[0][2], last_fetch=mine[-1][2], flags=flags,
            ))
    return sorted(flagged, key=lambda a: (-len(a.flags), -a.fetches, str(a.account_id)))


async def report(db: AsyncSession, days: int, now: datetime.datetime | None = None) -> RulesAnomalies:
    """The flagged accounts over the last `days` days of the fetch log and the daily counts."""
    now = now or datetime.datetime.now(datetime.UTC)
    since = now - datetime.timedelta(days=days)
    fetches = await fetches_since(db, since)
    counts = await daily_counts_since(db, since.date(), [Capped.FILL_EVENT, Capped.RULES_TOKEN, Capped.RULES_FETCH])
    return RulesAnomalies(days=days, since=since, accounts=flag(fetches, counts, get_settings()))


def table(found: RulesAnomalies) -> str:
    """The report as a plain-text table, one row per flagged account (app/scripts/rules_anomalies.py)."""
    if not found.accounts:
        return f"No account flagged in the last {found.days} days."
    head = ("account", "fetches", "fills", "systems", "last fetch (UTC)", "flags")
    rows = [(str(a.account_id), str(a.fetches), str(a.fills), str(len(a.job_systems)),
             a.last_fetch.astimezone(datetime.UTC).strftime("%Y-%m-%d %H:%M"),
             "; ".join(f"{f.reason}: {f.detail}" for f in a.flags)) for a in found.accounts]
    widths = [max(len(r[i]) for r in [head, *rows]) for i in range(len(head) - 1)]
    lines = ["  ".join([*(c.ljust(w) for c, w in zip(r[:-1], widths)), r[-1]]).rstrip() for r in [head, *rows]]
    return "\n".join([lines[0], "  ".join("-" * w for w in widths) + "  -----", *lines[1:]])
