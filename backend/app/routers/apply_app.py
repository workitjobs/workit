"""
WorkIt Auto Apply's Model route (KAN-723, W1 of
docs/desktop_application_auto_apply.md; ADR 0005 in apply-agent/docs/adr/):
the desktop app makes every model call here, and WorkIt holds the provider
keys, counts each student's tokens and stops them at the monthly Usage cap.
A thin proxy: the prompts stay in the app.

POST /apply-app/model  ModelCall {kind?, model, system?, prompt, schema}
     One `ask`: the answer to `prompt` as JSON that fits `schema`, through
     the API's model chain (app/services/models.py): `haiku` asks the small
     chain, `sonnet` and `opus` the large one, so the model names stay in
     the SCOUT_* settings. The chain moves on at a 429, a 5xx, a request too
     large or an answer outside the schema (workit_scout.llm.complete_schema).
     The student's identity (name, email, phone, links) is removed from both
     texts on the way, whatever the app replaced first: an answer may then
     hold `[name]`, `[email]`, `[phone]` or `[link]`, which the app must not
     fill into a form. Answers ModelAnswer {answer, tokens, usage}.
       403  not a student's account.
       422  a body outside ModelCall (a schema that is not an object's, has a
            `$ref`, or is over 20,000 characters, app/schemas/apply_app.py).
       429  with Retry-After: the student's calls this minute are at
            APPLY_APP_CALLS_PER_MINUTE (a minute at most), or their tokens this
            month are at APPLY_APP_MONTHLY_TOKENS (Retry-After runs to the 1st,
            UTC; the app pauses its run until then). Nothing goes to a model.
       413  too large for every model in the chain.
       502  no model's answer fit the schema.
       503  with Retry-After: every model is busy, out of quota or down.
     The tokens a failed call spent still count.
GET  /apply-app/usage  Usage {used, cap, resets_at}: this month's tokens.

Logs name the student, the call's kind and model, and its tokens; never a
prompt or an answer.
"""

import datetime
import logging
import math

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from workit_scout.llm import LLM, InvalidReply, RequestTooLarge, ScoutUnavailable

from app.config import get_settings
from app.db import get_session
from app.deps import get_current_account
from app.queries import model_usage
from app.schemas.apply_app import ModelAnswer, ModelCall, Usage
from app.schemas.auth import AccountType, AuthenticatedAccount
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
    return Usage(used=used, cap=get_settings().apply_app_monthly_tokens, resets_at=model_usage.resets_at(now))


def _refused(code: int, message: str, wait: float) -> HTTPException:
    return HTTPException(code, message, headers={"Retry-After": str(max(1, math.ceil(wait)))})


@router.get("/usage")
async def usage(
    account: AuthenticatedAccount = Depends(_student),
    db: AsyncSession = Depends(get_session),
) -> Usage:
    now = _now()
    return _usage(await model_usage.used_this_month(db, account.id, now), now)


@router.post("/model")
async def model_call(
    body: ModelCall,
    account: AuthenticatedAccount = Depends(_student),
    db: AsyncSession = Depends(get_session),
    large: LLM = Depends(get_large_llm),
    small: LLM = Depends(get_small_llm),
) -> ModelAnswer:
    settings = get_settings()
    now = _now()
    used = await model_usage.take_call(db, account.id, settings.apply_app_calls_per_minute, now)
    if used is None:
        next_minute = now.replace(second=0, microsecond=0) + datetime.timedelta(minutes=1)
        raise _refused(status.HTTP_429_TOO_MANY_REQUESTS, "Too many model calls this minute.",
                       (next_minute - now).total_seconds())
    if used >= settings.apply_app_monthly_tokens:
        resets = model_usage.resets_at(now)
        raise _refused(status.HTTP_429_TOO_MANY_REQUESTS,
                       f"Monthly model use reached; resets on {resets:%B} {resets.day}.",
                       (resets - now).total_seconds())
    identity = await load_identity(db, account)
    # Hold no connection while the model writes, which can take a minute.
    await db.commit()

    messages = [{"role": "system", "content": body.system}] if body.system else []
    messages.append({"role": "user", "content": body.prompt})
    llm = small if body.model == "haiku" else large
    failure: ScoutUnavailable | None = None
    try:
        answer, spent = await llm.complete_schema(messages, body.answer_schema, identity=identity)
    except ScoutUnavailable as e:
        failure, spent = e, e.spent

    used = await model_usage.add_spent(db, account.id, spent, now)
    await db.commit()
    logger.info("Model route: student %s, %s on %s, %d tokens in, %d out%s", account.id, body.kind, body.model,
                spent.input_tokens, spent.output_tokens, f", failed: {type(failure).__name__}" if failure else "")
    if isinstance(failure, RequestTooLarge):
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, str(failure))
    if isinstance(failure, InvalidReply):
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(failure))
    if failure is not None:
        raise _refused(status.HTTP_503_SERVICE_UNAVAILABLE, str(failure), 60)
    return ModelAnswer(answer=answer, tokens=spent.total, usage=_usage(used, now))
