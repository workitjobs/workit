"""
fill_answers' write behind PATCH .../fill-answers (routers/profiles.py): Apply's
Answer bank changes merged into the student's `applicant_profiles.fill_answers`
(KAN-746), by services/apply_answers.py's rules.
"""

import datetime
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profiles import Applicant_Profile
from app.schemas.profile import FillAnswersChange
from app.services import apply_answers

# One student's brought answers at most; a bank past it is refused, not cut.
MAX_ANSWERS = 2000


class TooMany(Exception):
    pass


def _utc(at: datetime.datetime | None) -> datetime.datetime | None:
    return None if at is None else at if at.tzinfo else at.replace(tzinfo=datetime.UTC)


async def merge_from_apply(db: AsyncSession, applicant_id: uuid.UUID, change: FillAnswersChange) -> apply_answers.Merged | None:
    """Lays `change` on the stored answers and writes them back; flushes, never
    commits. The row is locked first (FOR UPDATE), so two syncs at once each
    merge into the other's result. None with no profile; raises TooMany when
    the merged answers pass MAX_ANSWERS."""
    profile = await db.scalar(
        select(Applicant_Profile).where(Applicant_Profile.id == applicant_id).with_for_update()
    )
    if profile is None:
        return None
    changes = [
        (a.question, apply_answers.brought(a.answer, options=a.options, source=a.source, reviewed=a.reviewed,
                                           company=a.company), _utc(a.edited_at))
        for a in change.answers
    ] + [(d.question, None, _utc(d.edited_at)) for d in change.deleted]
    merged = apply_answers.merge(profile.fill_answers or {}, changes, datetime.datetime.now(datetime.UTC))
    if len(merged.answers) > MAX_ANSWERS:
        raise TooMany(f"At most {MAX_ANSWERS} saved answers.")
    profile.fill_answers = merged.answers
    await db.flush()
    return merged
