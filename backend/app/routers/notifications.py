"""
GET and POST for the top bar's bell (KAN-298).

    GET /applicants/{applicant_id}/notifications?limit=20
        Newest first, plus unread_count in the same response (one round
        trip for the bell's list and its badge).

    POST /applicants/{applicant_id}/notifications/read
        Marks rows read: with a body {"ids": [...]}, those rows (the bell
        marks a row read when the student opens it, and a grouped row's
        repeats with it); with no body, every unread row (the bell's Mark
        All Read). Opening the bell marked everything read until KAN-829,
        which left Mark All Read nothing to do.

The only writer is app/services/job_alerts.py; nothing here creates a
notification.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import owned_applicant
from app.queries.notifications import fetch_notifications, mark_read
from app.schemas.notification import NotificationList, ReadNotifications

router = APIRouter()

_PATH = "/applicants/{applicant_id}/notifications"


@router.get(_PATH, response_model=NotificationList)
async def get_notifications(
    limit: int = Query(20, ge=1, le=100),
    applicant_id: uuid.UUID = Depends(owned_applicant),
    session: AsyncSession = Depends(get_session),
) -> NotificationList:
    rows, unread_count = await fetch_notifications(session, applicant_id, limit)
    return NotificationList(notifications=rows, unread_count=unread_count)


@router.post(_PATH + "/read", response_model=NotificationList)
async def read_notifications(
    body: ReadNotifications | None = None,
    applicant_id: uuid.UUID = Depends(owned_applicant),
    session: AsyncSession = Depends(get_session),
) -> NotificationList:
    await mark_read(session, applicant_id, body.ids if body else None)
    await session.commit()
    rows, unread_count = await fetch_notifications(session, applicant_id, limit=20)
    return NotificationList(notifications=rows, unread_count=unread_count)
