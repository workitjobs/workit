"""
Reading an upload's text into the bank's entries and skills (KAN-732, ADR
0007): the model first while the student has an AI reading left today, the
parser behind it (`bank_import.read_resume`). Upload, the parse preview,
Import Updated Resume and Import Again all read through here.

A reading the model made counts one PARSING use (`services/usage.py`); a
parser's reading counts none. Every reading adds one row to the reading log
(KAN-898, `models/resume_readings.py`): the route, the reader, why the
parser's reading was saved, the time and the counts, never the text. Like
every service it flushes and never commits: the route commits the use and
the row with its bank writes, so a failed save counts and logs nothing.
"""

import time
import uuid
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession
from workit_scout.llm import LLM

from app.models.resume_readings import MODEL_NAME_LENGTH, Resume_Reading
from app.schemas.auth import AuthenticatedAccount
from app.services.bank_import import Reading, read_resume
from app.services.identity import load_identity
from app.services.usage import Feature, count_use, uses_left

Route = Literal["upload", "preview", "update", "import_again"]


async def read_upload(
    session: AsyncSession,
    applicant_id: uuid.UUID,
    account: AuthenticatedAccount,
    raw_text: str | None,
    llm: LLM,
    *,
    route: Route,
) -> tuple[Reading, int]:
    """The reading, and the AI readings the student has left after it."""
    left = await uses_left(session, applicant_id, Feature.PARSING)
    # No model when no AI reading is left today: read_resume names why
    ask = left > 0 and bool(raw_text)
    identity = await load_identity(session, account) if ask else None
    started = time.monotonic()
    reading = await read_resume(raw_text, llm if ask else None, identity)
    duration_ms = round((time.monotonic() - started) * 1000)
    if reading.read_by == "model":
        await count_use(session, applicant_id, Feature.PARSING)
        left -= 1
    session.add(Resume_Reading(
        applicant_id=applicant_id, route=route, read_by=reading.read_by, reason=reading.reason,
        duration_ms=duration_ms, entries=len(reading.entries), skills=len(reading.skills),
        fields_dropped=reading.fields_dropped,
        # Clipped to the column: a longer name must never fail the upload
        model=reading.model[:MODEL_NAME_LENGTH] if reading.model else None,
        input_tokens=reading.input_tokens, output_tokens=reading.output_tokens,
    ))
    await session.flush()
    return reading, left
