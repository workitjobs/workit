"""
WorkIt Auto Apply's Model route (KAN-723, W1 of
docs/desktop_application_auto_apply.md; ADR 0005 in apply-agent/docs/adr/):
the desktop app makes every model call here, and WorkIt holds the provider
keys, builds the prompts (D5), counts each student's tokens and stops them
at the monthly Usage cap.

POST /apply-app/ask  AskCall {kind, version?, data}
     One of Apply's `ask`s, built on the server: `kind` names it
     ("writing.check"), and `data` is what the app collected for it, checked
     against the kind's own model (app/apply_prompts/). The server builds
     the system prompt, the prompt and the schema, so a request carries no
     instructions and no schema. Each kind runs on the size of the API's
     model chain it names (app/services/models.py).
POST /apply-app/model  ModelCall {kind?, model, system?, prompt, schema}
     The same call with the app's own prompt and schema, until every kind
     is ported; then it goes, with ModelCall's schema guards
     (app/schemas/apply_app.py). `haiku` asks the small chain, `sonnet` and
     `opus` the large one.

Both: the chain moves on at a 429, a 5xx, a request too large, a 400 or
422 (the provider refused this request or its schema) or an answer outside
the schema (workit_scout.llm.complete_schema). The student's email, phone
and links, and any email, phone or link found by pattern, go to the model
as placeholders, whatever the app replaced first, and come back in the
answer as their values (workit_scout.identity.Masked). The name is the
app's to replace (D8): the server's name removal also took ordinary words
("will" for a student named Will) and broke the prompt. Both answer
ModelAnswer {answer, tokens, usage}.
       403  not a student's account.
       422  a body outside AskCall or ModelCall, an unknown kind or version,
            or data outside the kind's model. Nothing counts.
       429  with Retry-After: the student's calls this minute are at
            APPLY_APP_CALLS_PER_MINUTE (a minute at most), or their tokens this
            month are at APPLY_APP_MONTHLY_TOKENS (Retry-After runs to the 1st,
            UTC; the app pauses its run until then). Nothing goes to a model.
       413  too large for every model in the chain.
       502  no model's answer fit the schema, or every model refused the
            request: asking again the same way will not help.
       503  with Retry-After: every model is busy, out of quota or down, or
            the API's model settings are wrong (a key, a model name).
     The tokens a failed call spent still count.
GET  /apply-app/usage  Usage {used, cap, resets_at}: this month's tokens.

Logs name the student, the call's kind and model size, and its tokens;
never a prompt or an answer.
"""

import dataclasses
import datetime
import logging
import math

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from workit_scout.llm import LLM, InvalidReply, RequestTooLarge, ScoutUnavailable

from app.apply_prompts import KINDS, said
from app.config import get_settings
from app.db import get_session
from app.deps import get_current_account
from app.queries import model_usage
from app.schemas.apply_app import AskCall, ModelAnswer, ModelCall, Usage
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
    built = said(kind.build(data), data)
    messages = [{"role": "system", "content": built.system}, {"role": "user", "content": built.prompt}]
    return await _call(db, account, small if kind.size == "small" else large, messages, built.schema,
                       kind.name, kind.size)


@router.post("/model")
async def model_call(
    body: ModelCall,
    account: AuthenticatedAccount = Depends(_student),
    db: AsyncSession = Depends(get_session),
    large: LLM = Depends(get_large_llm),
    small: LLM = Depends(get_small_llm),
) -> ModelAnswer:
    messages = [{"role": "system", "content": body.system}] if body.system else []
    messages.append({"role": "user", "content": body.prompt})
    return await _call(db, account, small if body.model == "haiku" else large, messages, body.answer_schema,
                       body.kind, body.model)


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
    if used >= settings.apply_app_monthly_tokens:
        resets = model_usage.resets_at(now)
        raise _refused(status.HTTP_429_TOO_MANY_REQUESTS,
                       f"Monthly model use reached; resets on {resets:%B} {resets.day}.",
                       (resets - now).total_seconds())
    # No name: the app replaces it (D8), and removing it here also took
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
