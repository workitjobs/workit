"""
Storing a bank's vector, and which banks need one (KAN-726). One place, so
the bank job (`app/scripts/embed_banks.py`) and a recommendations request
that embeds a new bank keep the same rule. Takes the caller's session and
never commits.

`embedded_at` is the bank version a vector was made from: the bank's
`updated_at` when it was read, not the time of the write. A bank is stale
when it has no vector or its `updated_at` has moved past that version
(`STALE`). Stamping the write's own time instead could miss a change: one
whose transaction began before the write but committed after it carries an
`updated_at` earlier than the write, so it would look embedded.
"""

import datetime
import uuid

from sqlalchemy import or_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bank import Experience_Bank

STALE = or_(
    Experience_Bank.embedding.is_(None),
    Experience_Bank.embedded_at.is_(None),
    Experience_Bank.embedded_at != Experience_Bank.updated_at,
)


async def store(
    session: AsyncSession, applicant_id: uuid.UUID, read_at: datetime.datetime, vector: list[float]
) -> bool:
    """Store `vector`, made from the bank as it was at `read_at` (its
    `updated_at` then), only if the bank has not changed since: a change in
    between already marked it stale again, and its notify wakes the bank job
    for the next version. False when the bank changed. `updated_at` stays the
    bank's last change: storing its vector is no change, and Home's kept
    result is keyed on it (queries/jobs/home.py)."""
    result = await session.execute(
        update(Experience_Bank)
        .where(Experience_Bank.applicant_id == applicant_id, Experience_Bank.updated_at == read_at)
        .values(embedding=vector, embedded_at=read_at, updated_at=read_at)
        .execution_options(synchronize_session=False)
    )
    return result.rowcount == 1
