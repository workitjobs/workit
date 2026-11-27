"""
What each application sent (W11, `docs/desktop_application_auto_apply.md`):
WorkIt Auto Apply keeps it here at the student's own Submit, so no Record of
it stays on their Mac, and the application's page shows it under What You
Sent.

PUT /applicants/{id}/applications/{job_id}/sent  SentApplicationBody -> 204
    Each question the form asked and the answer filled and read back, with
    `ai` on an answer AI wrote, in the form's order; it replaces one saved
    before. 404 with no application; 409 while the application is not
    applied or later (the app writes the stage first). A password, PIN or
    SSN answer never comes: the app cuts it out (apply.records.SECRET).
GET /applicants/{id}/applications/{job_id}/sent -> SentApplication
    404 with none saved.

Applicant accounts only, and only their own id (owned_applicant). The
answers are the student's own and go to no model.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import owned_applicant
from app.models.applications import Job_Application, Sent_Application
from app.models.dto import APPLIED_STAGES
from app.schemas.sent_applications import SentApplication, SentApplicationBody

router = APIRouter(prefix="/applicants/{applicant_id}/applications/{job_id}/sent", tags=["tracker"])


@router.put("", status_code=status.HTTP_204_NO_CONTENT)
async def put_sent(
    job_id: uuid.UUID,
    body: SentApplicationBody,
    applicant_id: uuid.UUID = Depends(owned_applicant),
    db: AsyncSession = Depends(get_session),
) -> Response:
    stage = await db.scalar(select(Job_Application.stage).where(
        Job_Application.applicant_id == applicant_id, Job_Application.job_id == job_id))
    if stage is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "You have no application for that job.")
    if stage not in APPLIED_STAGES:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only an application you sent keeps what it sent.")
    answers = [answer.model_dump() for answer in body.answers]
    upsert = pg_insert(Sent_Application).values(applicant_id=applicant_id, job_id=job_id, answers=answers)
    await db.execute(upsert.on_conflict_do_update(
        index_elements=[Sent_Application.applicant_id, Sent_Application.job_id],
        set_={"answers": answers, "sent_at": upsert.excluded.sent_at}))
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("", response_model=SentApplication)
async def get_sent(
    job_id: uuid.UUID,
    applicant_id: uuid.UUID = Depends(owned_applicant),
    db: AsyncSession = Depends(get_session),
) -> SentApplication:
    row = await db.get(Sent_Application, (applicant_id, job_id))
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nothing was kept of what this application sent.")
    return SentApplication(answers=row.answers, sent_at=row.sent_at)
