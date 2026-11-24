"""
The applicant's identity fields, loaded for the one function that removes
them (`workit_scout.identity`) before any text leaves for a model or for
Gemini's embeddings.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from workit_scout.identity import Identity

from app.models.profiles import Applicant_Profile
from app.schemas.auth import AuthenticatedAccount


async def load_identity(db: AsyncSession, account: AuthenticatedAccount) -> Identity:
    """The applicant's identity fields, which the model seam removes from
    every message before a model sees it."""
    profile = await db.get(Applicant_Profile, account.id)
    if profile is None:
        return Identity(name=account.full_name, email=account.email)
    return _of(profile)


async def load_applicant_identity(db: AsyncSession, applicant_id) -> Identity | None:
    """The same fields by the applicant's id, for a job with no signed-in
    account (the bank job, KAN-726). None when there is no profile row: the
    caller must then send nothing, since nothing could be removed."""
    profile = await db.get(Applicant_Profile, applicant_id)
    return None if profile is None else _of(profile)


def _of(profile: Applicant_Profile) -> Identity:
    return Identity(
        name=profile.full_name,
        email=profile.email,
        phone=profile.phone_number,
        links=(
            profile.linkedin_url,
            profile.portfolio_url,
            profile.github_url,
            profile.other_url,
        ),
    )
