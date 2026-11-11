"""
Reading an upload's text into the bank's entries and skills (KAN-732, ADR
0007): the model first while the student has an AI reading left today, the
parser behind it (`bank_import.read_resume`). Upload, the parse preview,
Import Updated Resume and Import Again all read through here.

A reading the model made counts one PARSING use (`services/usage.py`); a
parser's reading counts none. Like every service it flushes and never
commits: the route commits the use with its bank writes, so a failed save
counts nothing.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from workit_scout.llm import LLM

from app.schemas.auth import AuthenticatedAccount
from app.services.bank_import import Reading, read_resume
from app.services.identity import load_identity
from app.services.usage import Feature, count_use, uses_left


async def read_upload(
    session: AsyncSession,
    applicant_id: uuid.UUID,
    account: AuthenticatedAccount,
    raw_text: str | None,
    llm: LLM,
) -> tuple[Reading, int]:
    """The reading, and the AI readings the student has left after it."""
    left = await uses_left(session, applicant_id, Feature.PARSING)
    if left <= 0 or not raw_text:
        return await read_resume(raw_text), left
    reading = await read_resume(raw_text, llm, await load_identity(session, account))
    if reading.read_by == "model":
        await count_use(session, applicant_id, Feature.PARSING)
        left -= 1
    return reading, left
