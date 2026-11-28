"""
What each application sent (W11, `docs/desktop_application_auto_apply.md`):
WorkIt Auto Apply keeps it here at the student's own Submit, so no Record of
it stays on their Mac, and the application's page shows it under What You
Sent.

PUT /applicants/{id}/applications/{job_id}/sent  SentApplicationBody -> 204
    Each question the form asked and the answer it showed at the student's
    press, with `ai` on an answer AI wrote, in the form's order; it replaces
    one saved before. Each question's words are kept once for every
    application (form_questions), and the answers as [question id, answer,
    1 when AI wrote it]: on the Fill engine's 25 saved forms, 2.4 KB an
    application at the median, from 4.1 KB with the words and key names. 404 with no application; 409 while the application is not
    applied or later (the app writes the stage first). A password, PIN or
    SSN answer never comes: the app cuts it out (apply.records.SECRET).
GET /applicants/{id}/applications/{job_id}/sent -> SentApplication
    404 with none saved.

Applicant accounts only, and only their own id (owned_applicant). The
answers are the student's own and go to no model.
"""

import hashlib
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import owned_applicant
from app.models.applications import Form_Question, Job_Application, Sent_Application
from app.models.dto import APPLIED_STAGES
from app.schemas.sent_applications import (
    SentAnswer,
    SentApplication,
    SentApplicationBody,
)

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
    ids = await _question_ids(db, [answer.question for answer in body.answers])
    answers = [[ids[a.question], a.answer, *([1] if a.ai else [])] for a in body.answers]
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
    words = dict((await db.execute(select(Form_Question.id, Form_Question.text).where(
        Form_Question.id.in_({item[0] for item in row.answers})))).all())
    return SentApplication(sent_at=row.sent_at, answers=[
        SentAnswer(question=words[item[0]], answer=item[1], ai=len(item) > 2 and item[2] == 1)
        for item in row.answers if item[0] in words])


async def _question_ids(db: AsyncSession, questions: list[str]) -> dict[str, int]:
    """Each question's id in form_questions, its words added first where no form asked them before. Found by md5, as
    the unique index is, then matched by the words themselves."""
    texts = list(dict.fromkeys(questions))
    if not texts:
        return {}
    await db.execute(text("INSERT INTO form_questions (text) SELECT unnest(CAST(:texts AS text[]))"
                          " ON CONFLICT ((md5(text))) DO NOTHING"), {"texts": texts})
    hashes = [hashlib.md5(t.encode()).hexdigest() for t in texts]
    found = (await db.execute(select(Form_Question.id, Form_Question.text).where(
        func.md5(Form_Question.text).in_(hashes)))).all()
    return {words: id_ for id_, words in found}
