"""
The model behind Scout, and the only module in the API that imports `openai`.

Every provider Scout runs on speaks OpenAI's chat-completions format — Ollama
on a laptop, Gemini's compatibility endpoint, OpenAI itself — so choosing a
model is configuration (`SCOUT_*`, see settings.py), never code. That seam is
the reason this file exists; keep provider-specific behaviour out of the rest
of this package.
"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any, TypeVar

from jsonschema import Draft202012Validator
from openai import APIConnectionError, APIStatusError, AsyncOpenAI, RateLimitError
from pydantic import BaseModel, ValidationError
from referencing import Registry

from workit_scout.identity import Identity, Masked
from workit_scout.settings import Endpoint, ScoutSettings, Size

logger = logging.getLogger(__name__)

Message = dict[str, str]
T = TypeVar("T", bound=BaseModel)
R = TypeVar("R")

OFFLINE = "Scout is offline right now. Try again in a minute."
OUT_OF_QUOTA = "Scout has hit today's limit. Try again tomorrow."
CUT_OFF = "Scout lost its connection mid-reply. Try asking again."


INVALID = "The model's answer came back in the wrong shape. Try again."
TOO_LARGE = "This is too long for the model to read. Try something shorter."
TOO_LONG = "The model's answer ran past its length limit. Try again."


@dataclass(frozen=True)
class Spent:
    """The tokens a call cost at the providers: what they read (the prompt)
    and what they wrote (the reply, reasoning included)."""

    input_tokens: int = 0
    output_tokens: int = 0

    def __add__(self, other: "Spent") -> "Spent":
        return Spent(self.input_tokens + other.input_tokens, self.output_tokens + other.output_tokens)

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens


def _spent(usage) -> Spent:
    # Reasoning tokens are in total_tokens but not always in
    # completion_tokens (Gemini's compatibility endpoint), so the reply's
    # share is the total less the prompt.
    if usage is None:
        return Spent()
    read = usage.prompt_tokens or 0
    return Spent(read, max((usage.total_tokens or 0) - read, usage.completion_tokens or 0))


class ScoutUnavailable(Exception):
    """No configured model could answer. The message is written for the user.
    `spent` is what the endpoints tried cost first (`complete_schema`)."""

    spent: Spent = Spent()


class InvalidReply(ScoutUnavailable):
    """A structured reply that is not JSON or fails its schema."""


class ReplyCutOff(InvalidReply):
    """A structured reply the provider stopped at its token limit
    (`finish_reason` "length"): its JSON is cut off, so it would only fail
    the schema with a less helpful message."""


class RequestTooLarge(ScoutUnavailable):
    """The last endpoint tried found the request too large to read."""


# How providers word "too large" on a 400: OpenAI and Groq send the code
# `context_length_exceeded`, Gemini says the input token count exceeds the
# maximum. Groq answers a request over its tokens-a-minute limit with 413.
_TOO_LARGE_WORDS = ("context_length", "context length", "maximum context", "too large", "too long", "exceeds the maximum")


def _too_large(exc: Exception) -> bool:
    if not isinstance(exc, APIStatusError):
        return False
    if exc.status_code == 413:
        return True
    said = f"{exc.code or ''} {exc.message}".lower()
    return exc.status_code == 400 and any(w in said for w in _TOO_LARGE_WORDS)


def _worth_another_try(exc: Exception) -> bool:
    """
    Down, unreachable, out of quota or too small for the request: another
    provider may well answer (Gemini reads far more than Groq's free tier).
    Any other 4xx is a wrong key, model name or parameter — the fallback would
    get the same request, so stop and let the log say why.
    """
    if _too_large(exc):
        return True
    if isinstance(exc, APIStatusError):
        return isinstance(exc, RateLimitError) or exc.status_code >= 500
    return isinstance(exc, APIConnectionError)


def _busy(exc: Exception) -> bool:
    """A 5xx: the provider is overloaded or down for a moment. Gemini's free
    tier answered half of all requests with 503 "high demand" on 2026-11-23,
    and the same request a second later went through. A 429 is a quota that a
    pause does not lift, and an unreachable endpoint (a laptop with no Ollama)
    does not start in a second, so neither is asked again."""
    return isinstance(exc, APIStatusError) and exc.status_code >= 500


def _user_message(exc: Exception) -> str:
    if _too_large(exc):
        return TOO_LARGE
    return OUT_OF_QUOTA if isinstance(exc, RateLimitError) else OFFLINE


def _unavailable(failure: str) -> ScoutUnavailable:
    return RequestTooLarge(failure) if failure == TOO_LARGE else ScoutUnavailable(failure)


def _with(error: ScoutUnavailable, spent: Spent) -> ScoutUnavailable:
    error.spent = spent
    return error


def _effort(endpoint: Endpoint) -> dict[str, str]:
    # Sent only when set: not every provider accepts the parameter.
    if endpoint.reasoning_effort:
        return {"reasoning_effort": endpoint.reasoning_effort}
    return {}


def _log_failure(endpoint: Endpoint, exc: Exception) -> None:
    # Never the error's text: the SDK puts the provider's whole error body in
    # it, and Groq's holds the model's output (`failed_generation`); a
    # pydantic ValidationError holds the reply.
    if isinstance(exc, APIStatusError):
        said = f"HTTP {exc.status_code} {exc.code or ''}".rstrip()
    else:
        said = type(exc).__name__
    logger.warning(
        "Scout model %s at %s failed: %s", endpoint.model, endpoint.base_url, said
    )


def _in_json_string(value: str) -> str:
    return json.dumps(value)[1:-1]


def _deidentified(messages: Sequence[Message], identity: Identity) -> list[Message]:
    # The seam's own guarantee: every message, system prompt included, loses
    # its identity data here, whatever the caller already removed.
    return [{**m, "content": identity.remove(m["content"])} for m in messages]


class LLM:
    """
    Asks the endpoint chain, in order, for one reply. An endpoint that answers
    5xx is asked again after each pause in `BUSY_PAUSES`. It moves to the next
    endpoint when one is rate-limited (429), still erroring (5xx) or
    unreachable *before it has said anything*. Once text has reached the user a
    retry would repeat it, so a failure mid-reply ends the reply instead.
    """

    #: Seconds to wait before asking an endpoint that answered 5xx again, one
    #: entry a try: two more tries, a second and then two seconds later.
    BUSY_PAUSES: tuple[float, ...] = (1.0, 2.0)

    def __init__(self, endpoints: Sequence[Endpoint]):
        if not endpoints:
            raise ValueError("The endpoint chain is empty.")
        # Building a client opens no connection, so all are made up front.
        # max_retries=0: a daily cap does not lift after a backoff, and a
        # laptop without Ollama will not start one. Fail over at once; only
        # a 5xx is asked again, by `_again` (the SDK would retry a 429 too).
        self._endpoints = [
            (
                endpoint,
                AsyncOpenAI(
                    base_url=endpoint.base_url,
                    api_key=endpoint.api_key or "unused",
                    max_retries=0,
                ),
            )
            for endpoint in endpoints
        ]

    @classmethod
    def from_settings(cls, s: ScoutSettings, size: Size | None = None) -> "LLM":
        return cls(s.chain(size))

    async def _paused(self, endpoint: Endpoint, exc: Exception, tries: int) -> bool:
        """Whether to ask `endpoint` again after its `tries`th failure,
        `exc`: after the pause, when it was busy and pauses are left."""
        if not _busy(exc) or tries > len(self.BUSY_PAUSES):
            return False
        _log_failure(endpoint, exc)
        pause = self.BUSY_PAUSES[tries - 1]
        logger.info("Asking %s again in %ss", endpoint.model, pause)
        await asyncio.sleep(pause)
        return True

    async def _again(self, endpoint: Endpoint, ask: Callable[..., Awaitable[R]], *args: Any) -> R:
        """`ask(*args)`, asked again after each pause while it fails busy
        (5xx). The last failure is the caller's to log and handle."""
        tries = 0
        while True:
            tries += 1
            try:
                return await ask(*args)
            except APIStatusError as exc:
                if not await self._paused(endpoint, exc, tries):
                    raise

    async def stream(
        self, messages: Sequence[Message], *, identity: Identity
    ) -> AsyncIterator[str]:
        messages = _deidentified(messages, identity)
        failure = OFFLINE
        for endpoint, client in self._endpoints:
            started = False
            tries = 0
            while True:
                tries += 1
                try:
                    async for delta in self._complete(client, endpoint, messages):
                        started = True
                        yield delta
                    return
                except (APIConnectionError, APIStatusError) as exc:
                    # Before any text only: once some has reached the user,
                    # asking again would send it twice.
                    if not started and await self._paused(endpoint, exc, tries):
                        continue
                    _log_failure(endpoint, exc)
                    if started:
                        raise ScoutUnavailable(CUT_OFF) from exc
                    if not _worth_another_try(exc):
                        raise ScoutUnavailable(OFFLINE) from exc
                    failure = _user_message(exc)
                    break
        raise _unavailable(failure)

    async def complete_json(
        self,
        messages: Sequence[Message],
        schema: type[T],
        *,
        identity: Identity,
        max_tokens: int | None = None,
        wait: float | None = None,
    ) -> T:
        """
        One whole reply, not streamed, as JSON checked against `schema`. Nothing
        reaches the user until it returns, so every endpoint in the chain may
        be tried. A reply that fails the check is rejected, not repaired: the
        caller decides whether to ask again. `max_tokens` caps the reply,
        reasoning included; a reply stopped at the cap raises `ReplyCutOff`.
        `wait` is how many seconds each endpoint gets: one that has not
        answered by then is given up and the next is asked, as at a 503.
        Unset, an endpoint is waited for as long as the client allows.
        """
        messages = _deidentified(messages, identity)
        failure = OFFLINE
        for endpoint, client in self._endpoints:
            try:
                # `wait` covers the tries after a 5xx too: it is the
                # endpoint's whole time.
                text = await asyncio.wait_for(
                    self._again(
                        endpoint, self._complete_json, client, endpoint, messages, schema, max_tokens
                    ),
                    wait,
                )
            except TimeoutError as exc:
                # A stalled provider is treated as a down one: the next may
                # answer at once, and the caller is waiting on the reply.
                _log_failure(endpoint, exc)
                continue
            except (APIConnectionError, APIStatusError) as exc:
                _log_failure(endpoint, exc)
                if not _worth_another_try(exc):
                    raise ScoutUnavailable(OFFLINE) from exc
                failure = _user_message(exc)
                continue
            try:
                return schema.model_validate_json(text)
            except ValidationError as exc:
                _log_failure(endpoint, exc)
                raise InvalidReply(INVALID) from exc
        raise _unavailable(failure)

    async def complete_schema(
        self,
        messages: Sequence[Message],
        schema: dict[str, Any],
        *,
        identity: Identity,
    ) -> tuple[Any, Spent]:
        """
        `complete_json` for a caller whose schema is JSON Schema data, not a
        Pydantic class: WorkIt Auto Apply's prompts, through the Model route
        (KAN-723). The caller has checked the schema
        (`Draft202012Validator.check_schema`). A reply that is not JSON, fails
        the schema or is cut off moves down the chain, as a 429 does, since
        another model may well fit it, and so does a 400 or 422: it refuses
        this request, not the endpoint (Groq's `json_validate_failed`, or a
        schema the provider takes no part of). One that fails on every
        endpoint raises `InvalidReply`. Returns the answer and the tokens
        every endpoint tried spent; a failure carries them as `spent`.

        Identity data goes to the model as placeholders (`Masked`) and comes
        back in the answer as its values, since the caller types the answer
        into forms. The answer is checked with the values back in, so what
        the caller gets is what fits the schema.
        """
        mask = Masked(identity, (m["content"] for m in messages))
        messages = [{**m, "content": mask.hide(m["content"])} for m in messages]
        # An empty registry: by default jsonschema fetches a remote `$ref`'s
        # URL, and this schema came from outside the API.
        check = Draft202012Validator(schema, registry=Registry())
        failure = OFFLINE
        spent = Spent()
        for endpoint, client in self._endpoints:
            try:
                text, used = await self._again(
                    endpoint, self._complete_schema, client, endpoint, messages, "answer", schema
                )
            except ReplyCutOff as cut:
                spent += cut.spent
                failure = INVALID
                continue
            except (APIConnectionError, APIStatusError) as exc:
                _log_failure(endpoint, exc)
                if _worth_another_try(exc):
                    failure = _user_message(exc)
                elif isinstance(exc, APIStatusError) and exc.status_code in (400, 422):
                    failure = INVALID
                else:
                    raise _with(ScoutUnavailable(OFFLINE), spent) from exc
                continue
            spent += used
            try:
                answer = json.loads(mask.put_back(text, _in_json_string))
            # RecursionError: an answer nested thousands deep.
            except (ValueError, RecursionError):
                # Never the text itself in a log: it can echo the prompt.
                logger.warning("Model %s at %s answered no JSON", endpoint.model, endpoint.base_url)
                failure = INVALID
                continue
            if wrong := next(check.iter_errors(answer), None):
                logger.warning(
                    "Model %s at %s answered outside the schema: %s at %s",
                    endpoint.model, endpoint.base_url, wrong.validator, list(wrong.absolute_path),
                )
                failure = INVALID
                continue
            return answer, spent
        raise _with(InvalidReply(INVALID) if failure == INVALID else _unavailable(failure), spent)

    async def _complete_json(
        self,
        client: AsyncOpenAI,
        endpoint: Endpoint,
        messages: Sequence[Message],
        schema: type[BaseModel],
        max_tokens: int | None = None,
    ) -> str:
        text, _ = await self._complete_schema(
            client, endpoint, messages, schema.__name__, schema.model_json_schema(), max_tokens
        )
        return text

    async def _complete_schema(
        self,
        client: AsyncOpenAI,
        endpoint: Endpoint,
        messages: Sequence[Message],
        name: str,
        schema: dict[str, Any],
        max_tokens: int | None = None,
    ) -> tuple[str, Spent]:
        """One structured reply's text and what it cost."""
        # `max_tokens`, not `max_completion_tokens`: Ollama, Groq and Gemini's
        # compatibility endpoint all accept it. Sent only when set.
        limit = {"max_tokens": max_tokens} if max_tokens else {}
        # Not strict: providers disagree on which schemas strict mode accepts,
        # and the caller's check is what decides anyway.
        response = await client.chat.completions.create(
            model=endpoint.model,
            messages=list(messages),
            response_format={
                "type": "json_schema",
                "json_schema": {"name": name, "schema": schema},
            },
            **_effort(endpoint),
            **limit,
        )
        choice = response.choices[0]
        if choice.finish_reason == "length":
            _log_failure(endpoint, ReplyCutOff(TOO_LONG))
            raise _with(ReplyCutOff(TOO_LONG), _spent(response.usage))
        return choice.message.content or "", _spent(response.usage)

    async def _complete(
        self, client: AsyncOpenAI, endpoint: Endpoint, messages: Sequence[Message]
    ) -> AsyncIterator[str]:
        stream = await client.chat.completions.create(
            model=endpoint.model,
            messages=list(messages),
            stream=True,
            **_effort(endpoint),
        )
        # The context manager closes the connection when the caller stops
        # reading early, which is also what stops the provider generating.
        async with stream:
            async for chunk in stream:
                if chunk.choices and (delta := chunk.choices[0].delta.content):
                    yield delta
