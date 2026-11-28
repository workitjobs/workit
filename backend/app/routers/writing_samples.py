"""
A student's writing samples (KAN-384): up to three pieces of their own
writing, from which their Claude builds a style card through the connector
(app/connector/tools.py), so their answers read the way they write.

    GET /applicants/{applicant_id}/writing-samples
        {"samples": [{"id", "text"}], "style_card": str | null}, samples
        oldest first. style_card is null until their Claude builds one.

    POST /applicants/{applicant_id}/writing-samples {"text"}
        Adds one: 201 with {"id", "text"}. 409 when they have three already,
        422 for an empty one or one over 10,000 characters.

    PUT /applicants/{applicant_id}/writing-samples/{sample_id} {"text"}
        Replaces one's text: 200 with {"id", "text"}; 404 when it isn't theirs.

    DELETE /applicants/{applicant_id}/writing-samples/{sample_id}
        Removes one: 204; 404 when it isn't theirs.

    PUT /applicants/{applicant_id}/style-card {"card"}
        The student's own words for the card, in place of their Claude's:
        204. 409 with no samples (a card describes their own writing), 422
        for an empty one or one over CARD_MAX characters.

    DELETE /applicants/{applicant_id}/style-card
        Removes it: 204, also when there was none. Their Claude builds a
        new one the next time it writes.

Every change to the samples deletes the style card, so the card always
describes the samples the student has now; their Claude builds a new one
the next time it writes. The card goes into every answer their Claude
writes and every essay WorkIt Auto Apply writes (W11), which is why the
student can read and change it on Application Info. Samples go to no
model of WorkIt's but WorkIt Auto Apply's essays, with the student's
identity masked.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import owned_applicant
from app.queries import writing
from app.schemas.writing import MAX_SAMPLES, CardBody, Sample, SampleBody, Samples

router = APIRouter()

_PATH = "/applicants/{applicant_id}/writing-samples"


@router.get(_PATH, response_model=Samples)
async def get_samples(
    applicant_id: uuid.UUID = Depends(owned_applicant),
    session: AsyncSession = Depends(get_session),
) -> Samples:
    return Samples(
        samples=await writing.fetch_samples(session, applicant_id),
        style_card=await writing.fetch_style_card(session, applicant_id),
    )


@router.post(_PATH, response_model=Sample, status_code=201)
async def add_sample(
    body: SampleBody,
    applicant_id: uuid.UUID = Depends(owned_applicant),
    session: AsyncSession = Depends(get_session),
) -> Sample:
    try:
        sample = await writing.add_sample(session, applicant_id, body.text)
    except writing.TooMany:
        raise HTTPException(409, f"You can keep {MAX_SAMPLES} writing samples. Replace or remove one first.")
    await session.commit()
    return sample


@router.put(_PATH + "/{sample_id}", response_model=Sample)
async def replace_sample(
    sample_id: uuid.UUID,
    body: SampleBody,
    applicant_id: uuid.UUID = Depends(owned_applicant),
    session: AsyncSession = Depends(get_session),
) -> Sample:
    sample = await writing.replace_sample(session, applicant_id, sample_id, body.text)
    if sample is None:
        raise HTTPException(404, "Writing sample not found")
    await session.commit()
    return sample


@router.delete(_PATH + "/{sample_id}", status_code=204)
async def remove_sample(
    sample_id: uuid.UUID,
    applicant_id: uuid.UUID = Depends(owned_applicant),
    session: AsyncSession = Depends(get_session),
) -> Response:
    if not await writing.remove_sample(session, applicant_id, sample_id):
        raise HTTPException(404, "Writing sample not found")
    await session.commit()
    return Response(status_code=204)


_CARD = "/applicants/{applicant_id}/style-card"


@router.put(_CARD, status_code=204)
async def save_card(
    body: CardBody,
    applicant_id: uuid.UUID = Depends(owned_applicant),
    session: AsyncSession = Depends(get_session),
) -> Response:
    if not await writing.sample_texts(session, applicant_id):
        raise HTTPException(409, "Add a writing sample first: a style card describes your own writing.")
    await writing.save_style_card(session, applicant_id, body.card.strip())
    await session.commit()
    return Response(status_code=204)


@router.delete(_CARD, status_code=204)
async def remove_card(
    applicant_id: uuid.UUID = Depends(owned_applicant),
    session: AsyncSession = Depends(get_session),
) -> Response:
    await writing.drop_card(session, applicant_id)
    await session.commit()
    return Response(status_code=204)
