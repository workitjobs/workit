"""
The reading log's admin reads (KAN-898, models/resume_readings.py). Rows past
90 days go in the daily purge (services/retention.py). The rows are written
by services/resume_reading.py's `read_upload`.

- `readings_by_day`: how many uploads each reader read per day, and why the
  parser's reading was saved, for `app.scripts.reading_report`.
- `reading_health` (KAN-953): what the admins' Resume Reading page shows
  for a period, behind `GET /admin/resume-reading`.
"""

import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_usage import AI_Usage_Counter
from app.models.resume_readings import Resume_Reading


async def readings_by_day(db: AsyncSession, *, days: int, now: datetime.datetime | None = None) -> list[dict]:
    """The last `days` days' readings by day (UTC), reader and reason, newest
    day first, the model's before the parser's: how many, their mean time in
    seconds, and the mean of the fields the check dropped where a reply was
    checked (None where none was)."""
    since = (now or datetime.datetime.now(datetime.UTC)) - datetime.timedelta(days=days)
    day = func.date(func.timezone("UTC", Resume_Reading.created_at)).label("day")
    rows = (await db.execute(
        select(
            day, Resume_Reading.read_by, Resume_Reading.reason, func.count().label("readings"),
            func.avg(Resume_Reading.duration_ms).label("ms"),
            func.avg(Resume_Reading.fields_dropped).label("dropped"),
        ).where(Resume_Reading.created_at >= since)
        .group_by(day, Resume_Reading.read_by, Resume_Reading.reason)
        .order_by(day.desc(), Resume_Reading.read_by, Resume_Reading.reason.nulls_first())
    )).all()
    return [
        {
            "day": r.day, "read_by": r.read_by, "reason": r.reason, "readings": r.readings,
            "seconds": round(float(r.ms) / 1000, 1),
            "fields_dropped": None if r.dropped is None else round(float(r.dropped), 1),
        }
        for r in rows
    ]


# The newest readings the page lists.
RECENT = 50


def _seconds(ms: float | None) -> float | None:
    return None if ms is None else round(float(ms) / 1000, 1)


def _cost(prices: dict[str, tuple[float, float]], model: str | None, read: int, written: int) -> float | None:
    """What the tokens cost at the model's paid price (dollars a million tokens,
    read and written), or None for a model with no price."""
    if model not in prices:
        return None
    per_read, per_written = prices[model]
    return round((read * per_read + written * per_written) / 1_000_000, 4)


async def reading_health(
    db: AsyncSession,
    *,
    days: int,
    cap: int,
    prices: dict[str, tuple[float, float]],
    now: datetime.datetime | None = None,
) -> dict:
    """The Resume Reading page's numbers for the last `days` days (UTC), today
    included: the readings per day by reader, why the parser's reading was
    saved (most first, with each reason's newest time), the model readings'
    median time, each model that replied (its readings, median time, tokens
    and their cost at `prices`; a None model is a model reading from before
    the log held the name), today's AI readings against `cap`, and the newest
    RECENT readings. Counts, times and account ids only, as the log holds."""
    now = now or datetime.datetime.now(datetime.UTC)
    today = now.astimezone(datetime.UTC).date()
    since = datetime.datetime.combine(
        today - datetime.timedelta(days=days - 1), datetime.time.min, tzinfo=datetime.UTC)
    R = Resume_Reading
    shown = R.created_at >= since
    day = func.date(func.timezone("UTC", R.created_at)).label("day")
    median_ms = func.percentile_cont(0.5).within_group(R.duration_ms)

    per_day: dict[datetime.date, dict[str, int]] = {}
    for d, read_by, readings in await db.execute(
        select(day, R.read_by, func.count()).where(shown).group_by(day, R.read_by)
    ):
        per_day.setdefault(d, {"model": 0, "parser": 0})[read_by] = readings

    reasons = (await db.execute(
        select(R.reason, func.count().label("readings"), func.max(R.created_at).label("last_at"))
        .where(shown, R.reason.is_not(None))
        .group_by(R.reason)
        .order_by(func.count().desc(), R.reason)
    )).all()

    median = (await db.execute(select(median_ms).where(shown, R.read_by == "model"))).scalar_one()

    models = (await db.execute(
        select(
            R.model, func.count().label("readings"), median_ms.label("ms"),
            func.coalesce(func.sum(R.input_tokens), 0).label("read"),
            func.coalesce(func.sum(R.output_tokens), 0).label("written"),
        )
        # Every reply a model gave, saved or not, and the model readings whose
        # row is from before the log held the model's name (a None model)
        .where(shown, or_(R.model.is_not(None), R.read_by == "model"))
        .group_by(R.model)
        .order_by(func.count().desc(), R.model)
    )).all()

    used = (await db.execute(
        select(AI_Usage_Counter.count).where(
            AI_Usage_Counter.feature == "parsing",
            AI_Usage_Counter.day == today,
            AI_Usage_Counter.account_id.is_(None),
        )
    )).scalar_one_or_none()

    recent = (await db.execute(select(R).where(shown).order_by(R.created_at.desc()).limit(RECENT))).scalars()

    return {
        "read_at": now,
        "today": {"used": used or 0, "cap": cap},
        "days": [
            {"day": d.isoformat(), "ai": n["model"], "parser": n["parser"]}
            for d, n in sorted(per_day.items())
        ],
        "reasons": [{"reason": r.reason, "readings": r.readings, "last_at": r.last_at} for r in reasons],
        "median_seconds": _seconds(median),
        "models": [
            {
                "model": m.model, "readings": m.readings, "median_seconds": _seconds(m.ms),
                "input_tokens": m.read, "output_tokens": m.written,
                "cost": _cost(prices, m.model, m.read, m.written),
            }
            for m in models
        ],
        "recent": [
            {
                "at": r.created_at, "account": str(r.applicant_id), "route": r.route, "read_by": r.read_by,
                "model": r.model, "reason": r.reason, "seconds": _seconds(r.duration_ms),
                "entries": r.entries, "skills": r.skills,
                "tokens": None if r.input_tokens is None else r.input_tokens + (r.output_tokens or 0),
            }
            for r in recent
        ],
    }
