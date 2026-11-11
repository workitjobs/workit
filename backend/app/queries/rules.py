"""
The Rules table's site tokens and fetch log (KAN-756), behind
routers/extension_rules.py. A token is kept only as its sha256, as the
connector's are (app/connector/oauth.py), so the table fetches nothing if
it leaks. Tokens are purged after a day and fetches after 90
(services/retention.py).
"""

import datetime
import hashlib
import secrets
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daily_counts import Daily_Count
from app.models.rules_access import Rules_Fetch, Rules_Token


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def issue_token(db: AsyncSession, account_id: uuid.UUID, job_system: str, minutes: int) -> tuple[str, datetime.datetime]:
    """A new site token for the account and job system, and when it stops working; flushes, the route commits."""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=minutes)
    db.add(Rules_Token(token_hash=_hash(token), account_id=account_id, job_system=job_system, expires_at=expires_at))
    await db.flush()
    return token, expires_at


async def token_system(db: AsyncSession, account_id: uuid.UUID, token: str) -> str | None:
    """The job system a live token of this account's fetches; None for an unknown, expired or other account's token."""
    return await db.scalar(select(Rules_Token.job_system).where(
        Rules_Token.token_hash == _hash(token),
        Rules_Token.account_id == account_id,
        Rules_Token.expires_at > datetime.datetime.now(datetime.UTC),
    ))


async def log_fetch(db: AsyncSession, account_id: uuid.UUID, job_system: str) -> None:
    """Records one fetch of a job system's table by the account; flushes, the route commits."""
    db.add(Rules_Fetch(account_id=account_id, job_system=job_system))
    await db.flush()


async def fetched_by(db: AsyncSession, job_systems: list[str]) -> list[uuid.UUID]:
    """Every account that fetched any of these job systems' tables in the log (all 90 days)."""
    return list((await db.scalars(
        select(Rules_Fetch.account_id).where(Rules_Fetch.job_system.in_(job_systems)).distinct()
    )).all())


async def fetches_since(db: AsyncSession, since: datetime.datetime) -> list[tuple[uuid.UUID, str, datetime.datetime]]:
    """Every fetch from `since` on as (account, job system, time), each account's in time order (the anomaly report)."""
    return [tuple(row) for row in (await db.execute(
        select(Rules_Fetch.account_id, Rules_Fetch.job_system, Rules_Fetch.created_at)
        .where(Rules_Fetch.created_at >= since)
        .order_by(Rules_Fetch.account_id, Rules_Fetch.created_at)
    )).all()]


async def daily_counts_since(db: AsyncSession, since: datetime.date, kinds: list[str]) -> list[tuple[uuid.UUID, str, datetime.date, int]]:
    """The daily cap counts (services/daily_caps.py) of these kinds from `since` on, as (account, kind, day, count)."""
    return [tuple(row) for row in (await db.execute(
        select(Daily_Count.account_id, Daily_Count.kind, Daily_Count.day, Daily_Count.count)
        .where(Daily_Count.day >= since, Daily_Count.kind.in_(kinds))
    )).all()]


async def fetch_history(db: AsyncSession, account_id: uuid.UUID) -> list[tuple[datetime.date, str, int]]:
    """One account's fetches in the log (all 90 days) as (UTC day, job system, count), oldest first."""
    day = func.date(func.timezone("UTC", Rules_Fetch.created_at))
    return [tuple(row) for row in (await db.execute(
        select(day, Rules_Fetch.job_system, func.count())
        .where(Rules_Fetch.account_id == account_id)
        .group_by(day, Rules_Fetch.job_system)
        .order_by(day, Rules_Fetch.job_system)
    )).all()]
