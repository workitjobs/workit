"""The two queries app/routers/notifications.py needs (KAN-298). No HTTP,
no HTTPException: a route decides the status code."""

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


async def fetch_notifications(
    session: AsyncSession, applicant_id: uuid.UUID, limit: int
) -> tuple[list[Notification], int]:
    """Newest first, up to `limit`, plus the applicant's total unread count
    (not capped by `limit` — the bell's badge counts every unread row, not
    just the ones shown)."""
    rows = list(
        await session.scalars(
            select(Notification)
            .where(Notification.applicant_id == applicant_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
    )
    unread_count = await session.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.applicant_id == applicant_id, Notification.read_at.is_(None))
    )
    return rows, unread_count or 0


async def mark_read(
    session: AsyncSession, applicant_id: uuid.UUID, ids: list[uuid.UUID] | None = None
) -> None:
    """Marks the applicant's unread rows read: those in `ids` (a row the bell
    opened), or every one when `ids` is None (Mark All Read). An id that is
    not this applicant's matches nothing."""
    where = [Notification.applicant_id == applicant_id, Notification.read_at.is_(None)]
    if ids is not None:
        where.append(Notification.id.in_(ids))
    await session.execute(update(Notification).where(*where).values(read_at=func.now()))
