"""
Resume reading for admins (KAN-953): who read each uploaded resume, from the
reading log (queries/resume_readings.py), for the page at
/admin/resume-reading.

GET /admin/resume-reading  ?days=1..90 (default 14)
    The last `days` days (UTC), today included.
    `today`: the AI readings every student used today, and the day's limit
    (the daily pool's share for reading uploads).
    `days`: per day with a reading, how many the model read (`ai`) and how
    many the rule-based parser read.
    `reasons`: why the parser's reading was saved, most first, each with
    its readings and its newest time (models/resume_readings.py's
    PARSER_REASONS).
    `median_seconds`: the median time of a reading the model made.
    `models`: each model that replied, most readings first: its readings,
    median seconds, tokens read and written, and what those tokens cost at
    the model's paid price (MODEL_PRICES; null when the model has none). A
    null `model` is the model readings logged before the model's name was.
    `accuracy`: the newest recorded scoring run (services/reading_scores.py),
    or null.
    `recent`: the newest 50 readings: the time, the account id, the route,
    the reader, the model, the reason, the seconds, the entries and skills
    found, and the tokens.
    Counts, times and account ids only: the log holds no resume text.
    Admins only (WORKIT_ADMINS, 403 to anyone else), as /admin/fill-health.
"""

import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.deps import get_admin
from app.queries.resume_readings import reading_health
from app.schemas.auth import AuthenticatedAccount
from app.services.reading_scores import last_run

router = APIRouter(tags=["resume-reading"])


class TodayUsed(BaseModel):
    used: int
    cap: int


class ReadingDay(BaseModel):
    day: str
    ai: int
    parser: int


class ReasonCount(BaseModel):
    reason: str
    readings: int
    last_at: datetime.datetime


class ModelReadings(BaseModel):
    model: str | None
    readings: int
    median_seconds: float | None
    input_tokens: int
    output_tokens: int
    cost: float | None


class ScoringRun(BaseModel):
    ran: str
    set: str
    resumes: int
    model: str
    parser: float
    ai: float
    combined: float


class RecentReading(BaseModel):
    at: datetime.datetime
    account: str
    route: str
    read_by: str
    model: str | None
    reason: str | None
    seconds: float
    entries: int
    skills: int
    tokens: int | None


class ReadingHealth(BaseModel):
    read_at: datetime.datetime
    today: TodayUsed
    days: list[ReadingDay]
    reasons: list[ReasonCount]
    median_seconds: float | None
    models: list[ModelReadings]
    accuracy: ScoringRun | None
    recent: list[RecentReading]


@router.get("/admin/resume-reading", response_model=ReadingHealth)
async def admin_resume_reading(
    days: int = Query(default=14, ge=1, le=90),
    _admin: AuthenticatedAccount = Depends(get_admin),
    db: AsyncSession = Depends(get_session),
) -> ReadingHealth:
    settings = get_settings()
    # The same limit services/usage.py holds every student's readings to
    cap = int(settings.ai_daily_pool * settings.ai_parsing_share)
    health = await reading_health(db, days=days, cap=cap, prices=settings.prices)
    return ReadingHealth(**health, accuracy=last_run())
