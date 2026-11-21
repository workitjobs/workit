"""
WorkIt Auto Apply's Model route (KAN-723, W1 of
docs/desktop_application_auto_apply.md; ADR 0005 in apply-agent/docs/adr/):
the desktop app makes every model call here, and WorkIt holds the provider
keys, builds the prompts (D5), counts each student's tokens and stops them
at the daily Usage cap.

POST /apply-app/ask  AskCall {kind, version?, data}
     One of Apply's `ask`s, built on the server: `kind` names it
     ("writing.check"), and `data` is what the app collected for it, checked
     against the kind's own model (app/apply_prompts/). The server builds
     the system prompt, the prompt and the schema, so a request carries no
     instructions and no schema. Each kind runs on the size of the API's
     model chain it names (app/services/models.py).
     The free-form POST /apply-app/model, which took the app's own prompt
     and schema, went once every kind was built here (2026-11-14).

The chain moves on at a 429, a 5xx, a request too large, a 400 or
422 (the provider refused this request or its schema) or an answer outside
the schema (workit_scout.llm.complete_schema). The student's email, phone
and own links, and any email or phone found by pattern, go to the model
as placeholders, whatever the app left out first, and come back in the
answer as their values (workit_scout.identity.Masked). Other links stay:
the calls read employers' links. The name is the
app's to replace (D8), by its exact value (the design doc's section 3.4):
the server's name removal also took ordinary words ("will" for a student
named Will) and broke the prompt. It answers
ModelAnswer {answer, tokens, usage}.
       403  not a student's account.
       422  a body outside AskCall, an unknown kind or version,
            or data outside the kind's model. Nothing counts.
       429  with Retry-After: the student's calls this minute are at
            APPLY_APP_CALLS_PER_MINUTE (a minute at most), or their tokens
            today are at APPLY_APP_DAILY_TOKENS (Retry-After runs to midnight,
            UTC; the app pauses its run until then). Nothing goes to a model.
            The check is before the call, so the last call of a day may pass
            the cap by its own tokens; the answer is never cut short.
       413  too large for every model in the chain.
       502  no model's answer fit the schema, or every model refused the
            request: asking again the same way will not help.
       503  with Retry-After: every model is busy, out of quota or down, or
            the API's model settings are wrong (a key, a model name).
     The tokens a failed call spent still count.
GET  /apply-app/usage  UsageNow {used, cap, resets_at, bank_version}: today's
     tokens, and the version of the student's Answer bank (W11, 0 with none),
     so the app, which asks before each Application, knows when its copy in
     memory is old, with no request of its own.
GET  /apply-app/types  The Question types Apply classifies questions and checks
     plans with: each type's front matter and the order to try them in
     (app/apply_prompts/guides.py, `served`), never a guide's body, which is
     prompt text. The same for every student; the app keeps the last copy.

The app's sign-in (W5, D12; app/services/app_sign_in.py has the flow):
POST /apply-app/sign-in  SignInStart {challenge} -> 201 SignInCode {code, expires_in, paste}
     The website's /app-sign-in page, signed in as the student: a one-time
     code bound to the app's PKCE challenge, for 5 minutes. `paste` is true
     only for WorkIt's admins, whose page may show the code to copy.
       403  not a student's account.
       429  with Retry-After: 10 sign-ins this hour already.
POST /apply-app/session  SessionTrade {code, verifier} -> AppSession
     The app, with no session yet: a new Supabase session for the code's
     account, once. The code goes at the first try, whatever its verifier.
       400  no code to trade: traded already, expired, or the verifier is
            not the challenge's. The app starts again.
       503  Supabase did not make the session.

The Fill engine's download (W7, D3, D27; app/services/engine_builds.py has
the storage and the key):
GET  /apply-app/engine?app_version=0.1.0 -> EngineDownload
     The newest published build that fits the app's version, encrypted with
     AES-GCM under a key made for this account, this Supabase session and
     this download, for KEY_TTL (2 minutes). The app checks the signature;
     the server never does.
       403  not a student's account, or a token with no session.
       404  no build fits this version: the app asks the student to update.
       422  an app_version that is not a version.
       503  Storage did not answer, or has no builds.json yet.
POST /apply-app/engine-key  EngineKeyAsk {key_id, expires_at} -> EngineKey {key}
     That download's key, for the same account and session only: another
     session's token makes another key, which opens nothing.
       410  past expires_at, or an expires_at further off than KEY_TTL.

Logs name the student, the call's kind and model size, and its tokens;
never a prompt or an answer.
"""

import base64
import dataclasses
import datetime
import logging
import math

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from workit_scout.llm import LLM, InvalidReply, RequestTooLarge, ScoutUnavailable

from app.apply_prompts import KINDS, guides, said
from app.config import get_settings
from app.db import get_session, get_supabase
from app.deps import get_current_account, is_admin
from app.queries import answer_banks, model_usage
from app.schemas.apply_app import (
    AppSession,
    AskCall,
    EngineDownload,
    EngineKey,
    EngineKeyAsk,
    ModelAnswer,
    SessionTrade,
    SignInCode,
    SignInStart,
    Usage,
    UsageNow,
)
from app.schemas.auth import AccountType, AuthenticatedAccount
from app.security import decode_access_token
from app.services import app_sign_in, engine_builds
from app.services.identity import load_identity
from app.services.models import get_large_llm, get_small_llm

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/apply-app", tags=["apply-app"])


def _student(account: AuthenticatedAccount = Depends(get_current_account)) -> AuthenticatedAccount:
    if account.account_type is not AccountType.APPLICANT:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "WorkIt Auto Apply is for job seekers.")
    return account


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


def _usage(used: int, now: datetime.datetime) -> Usage:
    return Usage(used=used, cap=get_settings().apply_app_daily_tokens, resets_at=model_usage.resets_at(now))


def _refused(code: int, message: str, wait: float) -> HTTPException:
    return HTTPException(code, message, headers={"Retry-After": str(max(1, math.ceil(wait)))})


@router.get("/usage")
async def usage(
    account: AuthenticatedAccount = Depends(_student),
    db: AsyncSession = Depends(get_session),
) -> UsageNow:
    now = _now()
    today = _usage(await model_usage.used_today(db, account.id, now), now)
    return UsageNow(**today.model_dump(), bank_version=await answer_banks.fetch_version(db, account.id) or 0)


@router.post("/sign-in", status_code=status.HTTP_201_CREATED)
async def sign_in(
    body: SignInStart,
    account: AuthenticatedAccount = Depends(_student),
    db: AsyncSession = Depends(get_session),
) -> SignInCode:
    try:
        code = await app_sign_in.start(db, account.id, body.challenge, _now())
    except app_sign_in.TooMany as e:
        raise _refused(status.HTTP_429_TOO_MANY_REQUESTS, "Too many sign-ins this hour. Try again later.",
                       e.wait) from None
    return SignInCode(code=code, expires_in=int(app_sign_in.CODE_TTL.total_seconds()), paste=is_admin(account))


@router.post("/session")
async def app_session(body: SessionTrade, db: AsyncSession = Depends(get_session)) -> AppSession:
    try:
        return AppSession(**await app_sign_in.trade(db, body.code, body.verifier, _now()))
    except app_sign_in.Over:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "That sign-in is over. Sign in again from WorkIt Auto Apply.") from None
    except app_sign_in.NoSession:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "WorkIt could not sign the app in. Try again.") from None


_bearer = HTTPBearer(auto_error=False)


async def _session_id(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> str:
    """The Supabase session the token belongs to, which an engine key is made for. get_current_account
    has already checked the token; this reads one more claim from it."""
    try:
        session = (await decode_access_token(credentials.credentials)).get("session_id") if credentials else None
    except jwt.InvalidTokenError:
        session = None
    if not isinstance(session, str) or not session:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Sign in from WorkIt Auto Apply.")
    return session


def _engine_secret() -> str:
    """What every engine key is made from: the service key, which only the API holds."""
    secret = get_settings().supabase_service_key
    if not secret:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "WorkIt can't send the Fill engine right now.")
    return secret


@router.get("/engine")
async def engine(
    app_version: str = Query(pattern=engine_builds.VERSION.pattern),
    account: AuthenticatedAccount = Depends(_student),
    session_id: str = Depends(_session_id),
) -> EngineDownload:
    try:
        build = engine_builds.newest_fit(await engine_builds.builds(get_supabase), app_version)
        data = await engine_builds.bundle(get_supabase, build["sha256"])
    except engine_builds.NoBuild:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            "No Fill engine fits this version of WorkIt Auto Apply. Update the app.") from None
    except Exception:
        logger.exception("Couldn't read the Fill engine's builds")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            "WorkIt can't send the Fill engine right now. Try again soon.") from None
    download = engine_builds.encrypt(build, data, _engine_secret(), str(account.id), session_id, _now())
    return EngineDownload(**dataclasses.asdict(download))


@router.post("/engine-key")
async def engine_key(
    body: EngineKeyAsk,
    account: AuthenticatedAccount = Depends(_student),
    session_id: str = Depends(_session_id),
) -> EngineKey:
    now = _now().timestamp()
    if not now < body.expires_at <= now + engine_builds.KEY_TTL.total_seconds():
        raise HTTPException(status.HTTP_410_GONE, "That Fill engine download has expired. Download it again.")
    key = engine_builds.key(_engine_secret(), str(account.id), session_id, body.key_id, body.expires_at)
    return EngineKey(key=base64.b64encode(key).decode())


@router.get("/types")
async def types(account: AuthenticatedAccount = Depends(_student)) -> Response:
    return Response(guides.served(), media_type="application/json")


@router.post("/ask")
async def ask(
    body: AskCall,
    account: AuthenticatedAccount = Depends(_student),
    db: AsyncSession = Depends(get_session),
    large: LLM = Depends(get_large_llm),
    small: LLM = Depends(get_small_llm),
) -> ModelAnswer:
    kind = KINDS.get((body.kind, body.version))
    if kind is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"No kind {body.kind!r} at version {body.version}.")
    try:
        data = kind.data.model_validate(body.data)
    except ValidationError as e:
        raise RequestValidationError([{**error, "loc": ("body", "data", *error["loc"])}
                                      for error in e.errors(include_url=False, include_context=False, include_input=False)]) from None
    built = said(kind.build(data), data) if kind.applicant else kind.build(data)
    messages = [{"role": "system", "content": built.system}, {"role": "user", "content": built.prompt}]
    return await _call(db, account, small if kind.size == "small" else large, messages, built.schema,
                       kind.name, kind.size)


async def _call(db: AsyncSession, account: AuthenticatedAccount, llm: LLM, messages: list[dict[str, str]],
                schema: dict, kind: str, model: str) -> ModelAnswer:
    """The limits, the cap, one call down the chain and its count."""
    settings = get_settings()
    now = _now()
    used = await model_usage.take_call(db, account.id, settings.apply_app_calls_per_minute, now)
    if used is None:
        next_minute = now.replace(second=0, microsecond=0) + datetime.timedelta(minutes=1)
        raise _refused(status.HTTP_429_TOO_MANY_REQUESTS, "Too many model calls this minute.",
                       (next_minute - now).total_seconds())
    if used >= settings.apply_app_daily_tokens:
        resets = model_usage.resets_at(now)
        raise _refused(status.HTTP_429_TOO_MANY_REQUESTS, "Today's model use is reached; it resets at midnight UTC.",
                       (resets - now).total_seconds())
    # No name: the app replaces it by its exact value (D8, the design doc's 3.4), and removing it here also took
    # ordinary words that are a part of it, such as "will" or "mark".
    identity = dataclasses.replace(await load_identity(db, account), name=None)
    # Hold no connection while the model writes, which can take a minute.
    await db.commit()

    failure: ScoutUnavailable | None = None
    try:
        answer, spent = await llm.complete_schema(messages, schema, identity=identity)
    except ScoutUnavailable as e:
        failure, spent = e, e.spent

    used = await model_usage.add_spent(db, account.id, spent, now)
    await db.commit()
    logger.info("Model route: student %s, %s on %s, %d tokens in, %d out%s", account.id, kind, model,
                spent.input_tokens, spent.output_tokens, f", failed: {type(failure).__name__}" if failure else "")
    if isinstance(failure, RequestTooLarge):
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, str(failure))
    if isinstance(failure, InvalidReply):
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(failure))
    if failure is not None:
        # Not Scout's message, which names Scout and can say "tomorrow".
        raise _refused(status.HTTP_503_SERVICE_UNAVAILABLE, "No model can answer right now. Try again in a minute.", 60)
    return ModelAnswer(answer=answer, tokens=spent.total, usage=_usage(used, now))
