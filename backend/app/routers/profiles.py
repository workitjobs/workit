"""GET and PATCH for the applicant's own profile fields, home location
included (KAN-372).

PATCH updates only the fields present in the body (`model_fields_set`), so a
field left out keeps its value. The name keeps its four columns in step
(app/services/names.py): parts sent (Settings' Personal Details) are merged
with the stored ones and joined into full_name; a full_name sent alone (the
resume editor's header) is split into parts. Both a first and a last name
are required, as at signup, and the joined name fits full_name's 50.

GET .../fill-profile is the Fill engine's own profile and policies for the
student (`fill_profile`, `fill_policies`; models/CLAUDE.md, "The Fill
engine's profile"), which the extension lays its own fields over. Only the
owner reads it: it holds their self-identification. Only
scripts/import_apply_profile.py writes the profile and policies; the answers
are also written by the PATCH below.

PATCH .../fill-answers {"answers": [...], "deleted": [...]} is Apply's sync of
its Answer bank (KAN-746, apply-agent docs/workit.md): each entry as Apply
keeps it (question, answer, options, source, reviewed, company, edited_at),
at most 200 of each, merged into `fill_answers` key by key, so the
extension's answer bank (GET .../answer-bank) has it with no import. WorkIt
decides `own` (services/apply_answers.py: `source: lisul`, never one marked
`reviewed: false`). A newer edit wins: a change older than the stored
entry's `edited_at` is left out and named in `kept`; the student's own
words they saved on WorkIt win over an older Apply answer when served
(written.answer_bank). An empty answer deletes. Answers {saved, deleted,
kept}. 404 with no profile, 422 past 2000 saved answers.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import assert_applicant_owns, get_current_account
from app.models.profiles import Applicant_Profile
from app.queries.fill_answers import TooMany, merge_from_apply
from app.schemas.auth import AuthenticatedAccount
from app.schemas.profile import (
    ApplicantProfileResponse,
    ApplicantProfileUpdate,
    FillAnswersChange,
    FillAnswersMerged,
    FillProfile,
)
from app.services.names import join_name, name_columns, split_name

NAME_PARTS = ("first_name", "middle_name", "last_name")

router = APIRouter()


@router.get(
    "/applicants/{applicant_id}/profile",
    response_model=ApplicantProfileResponse,    # serialize the return value through this Pydantic schema
)
async def get_profile(
    applicant_id: uuid.UUID,
    account: AuthenticatedAccount = Depends(get_current_account),
    session: AsyncSession = Depends(get_session),
) -> ApplicantProfileResponse:
    assert_applicant_owns(account, applicant_id)
    profile = await session.get(Applicant_Profile, applicant_id)    # gets the table and attach the applicant id
    if profile is None:
        raise HTTPException(404, "Profile not found")
    return ApplicantProfileResponse.model_validate(profile)         # makes sure response follows schema


@router.get("/applicants/{applicant_id}/fill-profile", response_model=FillProfile)
async def get_fill_profile(
    applicant_id: uuid.UUID,
    account: AuthenticatedAccount = Depends(get_current_account),
    session: AsyncSession = Depends(get_session),
) -> FillProfile:
    assert_applicant_owns(account, applicant_id)
    profile = await session.get(Applicant_Profile, applicant_id)
    if profile is None:
        raise HTTPException(404, "Profile not found")
    return FillProfile(profile=profile.fill_profile or {}, policies=profile.fill_policies or {})


@router.patch("/applicants/{applicant_id}/fill-answers", response_model=FillAnswersMerged)
async def sync_fill_answers(
    applicant_id: uuid.UUID,
    body: FillAnswersChange,
    account: AuthenticatedAccount = Depends(get_current_account),
    session: AsyncSession = Depends(get_session),
) -> FillAnswersMerged:
    assert_applicant_owns(account, applicant_id)
    try:
        merged = await merge_from_apply(session, applicant_id, body)
    except TooMany as exc:
        raise HTTPException(422, str(exc)) from exc
    if merged is None:
        raise HTTPException(404, "Profile not found")
    await session.commit()
    return FillAnswersMerged(saved=merged.saved, deleted=merged.deleted, kept=merged.kept)

# partial update
@router.patch(
    "/applicants/{applicant_id}/profile",
    response_model=ApplicantProfileResponse,    
)
async def update_profile(
    applicant_id: uuid.UUID,
    body: ApplicantProfileUpdate,
    account: AuthenticatedAccount = Depends(get_current_account),
    session: AsyncSession = Depends(get_session),
) -> ApplicantProfileResponse:
    assert_applicant_owns(account, applicant_id)
    profile = await session.get(Applicant_Profile, applicant_id)
    if profile is None:
        raise HTTPException(404, "Profile not found")

    sent = body.model_fields_set
    for field in sent - {"full_name", *NAME_PARTS}:
        setattr(profile, field, getattr(body, field))

    if sent & set(NAME_PARTS):
        stored = (
            (profile.first_name, profile.middle_name, profile.last_name)
            if profile.first_name
            else split_name(profile.full_name)
        )
        first, middle, last = (
            getattr(body, part) if part in sent else value for part, value in zip(NAME_PARTS, stored)
        )
        if not first or not last:
            raise HTTPException(422, "Enter a first and a last name.")
        if len(join_name(first, middle, last)) > 50:
            raise HTTPException(422, "Your name is too long: 50 characters at most in all.")
        for column, value in name_columns("", first, middle, last).items():
            setattr(profile, column, value)
    elif "full_name" in sent and body.full_name:
        for column, value in name_columns(body.full_name).items():
            setattr(profile, column, value)

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise HTTPException(500, "Failed to save profile changes")

    await session.refresh(profile)
    return ApplicantProfileResponse.model_validate(profile)
