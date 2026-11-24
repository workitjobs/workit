"""
The Fill engine's Rules table, one job system at a time (KAN-756): the
selectors, wordings and patterns the extension's fill reads, served after
sign-in instead of shipped, and only for the job system of the posting open.
This docstring is the contract the extension follows (backend/CLAUDE.md,
"The Rules table", has the design).

POST /extension/rules/token   {"url": <posting link>}
     Signed in (Bearer). The job system the link is on (auto_apply/hosts.py
     job_system_of), and a site token for it: {"token", "job_system",
     "expires_at", "expires_in"} (seconds; RULES_TOKEN_MINUTES, default 5).
     422 for a link on no job system WorkIt fills, 429 past
     RULES_TOKEN_DAILY_CAP a UTC day, 503 when the API has no table.
GET  /extension/rules   X-WorkIt-Site-Token: <token>
     Signed in (Bearer) as the token's account. The table the engine's
     loadRules takes, as is: the version, every answer rule and that one job
     system's data, watermarked for the account (services/rules_watermark.py).
     Logs the fetch (rules_fetches). 401 for a missing, unknown, expired or
     other account's token; 429 past RULES_FETCH_DAILY_CAP; 503 with no table.

Plain data only (the Chrome Web Store's line for fetched data): strings,
regex sources and names of functions the engine bundles, never steps,
expressions, or anything encrypted or encoded. Never cached by a browser or
proxy (Cache-Control: no-store): it is the account's own copy.
"""

import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auto_apply.hosts import job_system_of
from app.config import get_settings
from app.db import get_session
from app.deps import get_current_account
from app.queries import rules as queries
from app.schemas.auth import AuthenticatedAccount
from app.services import rules_table
from app.services.daily_caps import Capped, take_daily
from app.services.rules_watermark import watermark

router = APIRouter(tags=["extension-rules"])

NO_STORE = {"Cache-Control": "no-store"}


class SiteTokenRequest(BaseModel):
    url: str = Field(min_length=1, max_length=4096)


class SiteToken(BaseModel):
    token: str
    job_system: str
    expires_at: datetime.datetime
    expires_in: int


def _sites() -> set[str]:
    try:
        return rules_table.sites()
    except rules_table.NoRulesTable:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "WorkIt can't fill right now. Try again soon.") from None


@router.post("/extension/rules/token", response_model=SiteToken)
async def site_token(
    body: SiteTokenRequest,
    account: AuthenticatedAccount = Depends(get_current_account),
    db: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """A site token for the job system of the posting at `url`."""
    job_system = job_system_of(body.url.strip())
    if job_system is None or job_system not in _sites():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "WorkIt doesn't fill this site.")
    await take_daily(db, account.id, Capped.RULES_TOKEN)
    minutes = get_settings().rules_token_minutes
    token, expires_at = await queries.issue_token(db, account.id, job_system, minutes)
    await db.commit()
    return JSONResponse(
        SiteToken(token=token, job_system=job_system, expires_at=expires_at, expires_in=minutes * 60).model_dump(mode="json"),
        headers=NO_STORE,
    )


@router.get("/extension/rules")
async def site_rules(
    x_workit_site_token: str | None = Header(default=None, max_length=256),
    account: AuthenticatedAccount = Depends(get_current_account),
    db: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """The Rules table for the token's job system, watermarked for the account."""
    _sites()
    job_system = x_workit_site_token and await queries.token_system(db, account.id, x_workit_site_token)
    if not job_system:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "This site token is missing or has expired. Ask for a new one.")
    await take_daily(db, account.id, Capped.RULES_FETCH)
    await queries.log_fetch(db, account.id, job_system)
    await db.commit()
    return JSONResponse(watermark(rules_table.for_site(job_system), account.id), headers=NO_STORE)
