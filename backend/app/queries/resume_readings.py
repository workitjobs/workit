"""
The reading log's admin read (KAN-898, models/resume_readings.py): how many
uploads each reader read per day, and why the parser's reading was saved,
for `app.scripts.reading_report`. Rows past 90 days go in the daily purge
(services/retention.py). The rows are written by
services/resume_reading.py's `read_upload`.
"""

import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

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
