"""
The admins' anomaly report over the Rules table's fetch log (KAN-772,
services/rules_anomalies.py has the flags and their settings).

GET /admin/rules-anomalies  ?days=1..30 (default 7)
    The accounts whose fetches over the last `days` UTC days (today included;
    at most 30, as daily_counts keeps) look like scraping:
    each with its fetches, job systems, fills, first and last fetch, and the
    flags with their numbers. Admins only (WORKIT_ADMINS, 403 to anyone
    else), as /admin/fill-health. Never for students: it names accounts.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_admin
from app.schemas.auth import AuthenticatedAccount
from app.schemas.rules_anomalies import RulesAnomalies
from app.services.rules_anomalies import report

router = APIRouter(tags=["rules-anomalies"])


@router.get("/admin/rules-anomalies", response_model=RulesAnomalies)
async def admin_rules_anomalies(
    days: int = Query(default=7, ge=1, le=30),
    _admin: AuthenticatedAccount = Depends(get_admin),
    db: AsyncSession = Depends(get_session),
) -> RulesAnomalies:
    return await report(db, days)
