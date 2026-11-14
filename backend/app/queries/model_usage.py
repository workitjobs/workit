"""
The Model route's counts (KAN-723, routers/apply_app.py): each student's
tokens a calendar month (UTC) for the Usage cap, and their calls a minute.

A call takes a place in the student's minute (`take_call`) before it goes to
the providers and adds its tokens (`add_spent`) after, so the session holds
no connection while the model writes. Check, call, then count is not atomic:
two calls at once just under the cap both go, so the cap can be passed by a
call per Worker. That errs toward the student, as app/services/usage.py
does, while the cap protects free tiers rather than bills.

Each statement runs in the route's transaction, which the route commits.
"""

import datetime
import uuid

from sqlalchemy import case, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from workit_scout.llm import Spent

from app.models.model_usage import Model_Usage

_TABLE = Model_Usage.__table__
_USED = _TABLE.c.input_tokens + _TABLE.c.output_tokens


def month_of(now: datetime.datetime) -> datetime.date:
    return now.date().replace(day=1)


def resets_at(now: datetime.datetime) -> datetime.datetime:
    """When the month of `now` ends: the next month's first moment, UTC."""
    month = month_of(now)
    following = month.replace(year=month.year + 1, month=1) if month.month == 12 else month.replace(month=month.month + 1)
    return datetime.datetime.combine(following, datetime.time(), datetime.UTC)


def _minute(now: datetime.datetime) -> datetime.datetime:
    return now.replace(second=0, microsecond=0)


async def take_call(db: AsyncSession, applicant_id: uuid.UUID, per_minute: int, now: datetime.datetime) -> int | None:
    """Counts one call in the student's minute and returns their tokens used
    this month; None, with nothing counted, when this minute already holds
    `per_minute` calls."""
    minute = _minute(now)
    return await db.scalar(
        insert(_TABLE)
        .values(applicant_id=applicant_id, month=month_of(now), minute=minute, minute_calls=1)
        .on_conflict_do_update(
            index_elements=["applicant_id", "month"],
            set_={
                "minute": minute,
                "minute_calls": case((_TABLE.c.minute == minute, _TABLE.c.minute_calls + 1), else_=1),
            },
            where=or_(_TABLE.c.minute != minute, _TABLE.c.minute_calls < per_minute),
        )
        .returning(_USED)
    )


async def add_spent(db: AsyncSession, applicant_id: uuid.UUID, spent: Spent, now: datetime.datetime) -> int:
    """Adds one call's tokens to the student's month; returns the month's total."""
    used = await db.scalar(
        insert(_TABLE)
        .values(applicant_id=applicant_id, month=month_of(now), input_tokens=spent.input_tokens,
                output_tokens=spent.output_tokens, calls=1, minute=_minute(now), minute_calls=0)
        .on_conflict_do_update(
            index_elements=["applicant_id", "month"],
            set_={
                "input_tokens": _TABLE.c.input_tokens + spent.input_tokens,
                "output_tokens": _TABLE.c.output_tokens + spent.output_tokens,
                "calls": _TABLE.c.calls + 1,
            },
        )
        .returning(_USED)
    )
    return used


async def used_this_month(db: AsyncSession, applicant_id: uuid.UUID, now: datetime.datetime) -> int:
    used = await db.scalar(
        select(_USED).where(_TABLE.c.applicant_id == applicant_id, _TABLE.c.month == month_of(now))
    )
    return used or 0
