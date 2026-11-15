"""
WorkIt Auto Apply's sign-in (KAN-723, W5 of docs/desktop_application_auto_apply.md,
D12): the app signs in through the student's own browser and gets a Supabase
session of its own, with no port and no shared cookie.

1. The app makes a PKCE verifier and its S256 challenge (RFC 7636) and opens
   the website's /app-sign-in?challenge=... in the default browser.
2. The page, signed in as the student, asks `start` for a one-time code bound
   to that challenge, and gives it to the app: through the app's
   workit-auto-apply:// link, or the student pastes it (a Developer checkout,
   which macOS can't hand a link).
3. The app sends the code and the verifier to `trade`, which makes a new
   Supabase session for the account and answers it once.

A new session, not the website's: Supabase rotates a refresh token at each
use, so two holders of one session sign each other out. The service-role key
makes it: generate_link makes a magic link's token for the account's email and
sends no email, and Auth's /verify trades that token for a session, as a click
on the link would. PKCE makes a code useless to anyone but the app that asked
for it: a program that catches the link, or a code pasted anywhere else, has
no verifier.
"""

import asyncio
import base64
import datetime
import hashlib
import hmac
import logging
import secrets
import uuid

import httpx
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from supabase_auth.errors import AuthError

from app.config import get_settings
from app.db import get_supabase
from app.models.app_sign_in import App_Sign_In

logger = logging.getLogger(__name__)

# The app has this long to trade a code.
CODE_TTL = datetime.timedelta(minutes=5)
# A student's sign-ins an hour. Each trade makes a Supabase session, and Auth
# limits /verify by IP address, which is the API's own for every student.
PER_HOUR = 10
HOUR = datetime.timedelta(hours=1)


class TooMany(Exception):
    """The student's sign-ins this hour are at PER_HOUR; `wait` is the seconds
    until the oldest of them is an hour old."""

    def __init__(self, wait: float):
        super().__init__()
        self.wait = wait


class Over(Exception):
    """No code to trade: never made, traded already, expired, or the verifier
    is not the challenge's."""


class NoSession(Exception):
    """Supabase did not make the session."""


def _hash(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def challenge_of(verifier: str) -> str:
    """RFC 7636's S256: base64url(sha256(verifier)) with no padding."""
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()


async def start(db: AsyncSession, applicant_id: uuid.UUID, challenge: str, now: datetime.datetime) -> str:
    """A one-time code for the app whose challenge this is. Commits."""
    await db.execute(delete(App_Sign_In).where(App_Sign_In.created_at < now - HOUR))
    recent = list(await db.scalars(select(App_Sign_In.created_at)
                                   .where(App_Sign_In.applicant_id == applicant_id)
                                   .order_by(App_Sign_In.created_at)))
    if len(recent) >= PER_HOUR:
        raise TooMany((recent[-PER_HOUR] + HOUR - now).total_seconds())
    code = secrets.token_urlsafe(32)
    db.add(App_Sign_In(code_hash=_hash(code), applicant_id=applicant_id, challenge=challenge, created_at=now))
    await db.commit()
    return code


async def trade(db: AsyncSession, code: str, verifier: str, now: datetime.datetime) -> dict:
    """A new session for the code's account: {access_token, refresh_token,
    expires_at}. The code goes at the first try, whatever its verifier, so it
    can't be tried again. Commits."""
    row = (await db.execute(
        update(App_Sign_In)
        .where(App_Sign_In.code_hash == _hash(code),
               App_Sign_In.traded_at.is_(None),
               App_Sign_In.created_at > now - CODE_TTL)
        .values(traded_at=now)
        .returning(App_Sign_In.applicant_id, App_Sign_In.challenge)
    )).first()
    await db.commit()
    if row is None or not hmac.compare_digest(challenge_of(verifier), row.challenge):
        raise Over
    return await _new_session(row.applicant_id)


async def _new_session(applicant_id: uuid.UUID) -> dict:
    supabase = get_supabase()
    try:
        user = (await asyncio.to_thread(supabase.auth.admin.get_user_by_id, str(applicant_id))).user
        link = await asyncio.to_thread(supabase.auth.admin.generate_link, {"type": "magiclink", "email": user.email})
    except AuthError as e:
        logger.warning("app sign-in for %s: Supabase refused the link (%s)", applicant_id, e.code)
        raise NoSession from None
    session = await _verify(link.properties.hashed_token)
    if session is None:
        logger.warning("app sign-in for %s: Supabase refused the link's token", applicant_id)
        raise NoSession
    return {"access_token": session["access_token"], "refresh_token": session["refresh_token"],
            "expires_at": session.get("expires_at") or int(datetime.datetime.now(datetime.UTC).timestamp())
            + int(session["expires_in"])}


async def _verify(token_hash: str) -> dict | None:
    """Auth's /verify for a magic link's token: its session, or None. Not the
    shared client's verify_otp, which would keep the student's session on the
    service-role client every route uses. Logs no body: it holds the tokens."""
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            answer = await client.post(f"{settings.supabase_auth_url}/verify",
                                       json={"type": "magiclink", "token_hash": token_hash},
                                       headers={"apikey": settings.supabase_service_key or ""})
    except httpx.HTTPError as e:
        logger.warning("app sign-in: Auth's /verify did not answer (%s)", type(e).__name__)
        return None
    if answer.status_code != 200:
        logger.warning("app sign-in: Auth's /verify answered %s", answer.status_code)
        return None
    return answer.json()
