"""Groq in place of `claude -p` for `ask` (KAN-723, ../docs/desktop_application_auto_apply.md §8).

policies.yaml's `ask_model: groq` sends every `ask` (answers, essays, checks) to Groq's
OpenAI-compatible chat API; `drive` and `research` stay on `claude -p`. Apply's model names map to
Groq's gpt-oss models (`MODELS`, overridden key by key by `groq_models`). The key is GROQ_API_KEY,
else Keychain (service apply-groq, account api.groq.com); it is a developer's own key for testing,
never one shipped in an app (§8: a student build calls Groq through WorkIt).

Groq's strict JSON schema mode needs every property `required` and every object closed, so `strict`
rewrites a schema: a property the schema didn't require becomes nullable, and its null is dropped from
the answer, which then has the shape `claude -p` gives. A schema strict mode refuses (HTTP 400) is sent
again in best-effort mode, and every answer is checked against the schema (`_misfit`) before it returns.
"""

import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import datetime, timedelta

from apply import trace
from apply.adapters import SetupError, UsageLimitHit
from apply.claude_cli import ClaudeCLI, ClaudeError
from apply.keychain import GROQ, GROQ_HOST, MacKeychain

URL = "https://api.groq.com/openai/v1/chat/completions"
# Apply's model names (claude -p's), to Groq's: both gpt-oss models are production models that take
# strict schemas (console.groq.com/docs/models, read 2026-11-10); Scout runs on the same two.
MODELS = {"opus": "openai/gpt-oss-120b", "sonnet": "openai/gpt-oss-120b", "haiku": "openai/gpt-oss-20b"}
# Haiku's jobs are checks (claude_cli._argv gives it --effort low); the rest write.
EFFORT = {"haiku": "low"}
TIMEOUT = 180  # seconds for one reply; an essay on gpt-oss-120b takes a few
TRANSIENT_WAITS = (2, 5, 15)  # seconds before each retry of a 5xx, a timeout or a dropped connection
# Seconds: a 429 that asks for longer is a limit hit (UsageLimitHit), not a wait. A tokens-a-minute limit
# (8,000 on the free tier, seen 2026-11-10) always clears within a minute; a daily one asks for hours.
LONGEST_WAIT = 60
NO_KEY = ("no Groq key: set GROQ_API_KEY, or save it in Keychain with `security add-generic-password "
          "-s apply-groq -a api.groq.com -w` (it asks for the key), or set ask_model: claude in policies.yaml")
BAD_KEY = "Groq refused the key (HTTP {}): make a new one at console.groq.com/keys and save it again"
HEADERS = {"Content-Type": "application/json", "User-Agent": "workit-apply/0.1"}  # Groq's edge refuses urllib's own

# POSTs (url, body, headers) and returns (status, headers, body); an HTTP error is a status, not a raise.
Post = Callable[[str, bytes, dict], tuple[int, dict, bytes]]


def https_post(url: str, body: bytes, headers: dict) -> tuple[int, dict, bytes]:
    request = urllib.request.Request(url, body, headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as reply:
            return reply.status, dict(reply.headers), reply.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read()


def key(keychain=None) -> str | None:
    """The Groq API key: GROQ_API_KEY, else Keychain's; None with neither."""
    return os.environ.get("GROQ_API_KEY") or (keychain or MacKeychain(GROQ)).password(GROQ_HOST)


def live_claude(policies: dict, claude: ClaudeCLI | None = None, keychain=None):
    """The Claude adapter policies.yaml's ask_model names: claude (`claude -p`, the default) or groq."""
    claude = claude or ClaudeCLI()
    backend = policies.get("ask_model") or "claude"
    if backend == "claude":
        return claude
    if backend != "groq":
        raise SetupError(f"ask_model: {backend} in policies.yaml is neither claude nor groq")
    found = key(keychain)
    if not found:
        raise SetupError(NO_KEY)
    return GroqAsk(found, claude, models=MODELS | (policies.get("groq_models") or {}))


class GroqAsk:
    """The Claude adapter with `ask` on Groq. `drive`, `research` and anything else go to `claude`;
    `spent` counts both."""

    def __init__(self, api_key: str, claude: ClaudeCLI, models: dict[str, str] = MODELS, post: Post = https_post,
                 sleep: Callable[[float], None] = time.sleep, now: Callable[[], datetime] = datetime.now):
        self._key = api_key
        self._claude = claude
        self._models = models
        self._post = post
        self._sleep = sleep
        self._now = now
        self._spent = threading.local()  # tokens used by each thread's calls, as ClaudeCLI keeps them

    def __getattr__(self, name: str):
        return getattr(self._claude, name)

    def spent(self) -> int:
        return self._claude.spent() + getattr(self._spent, "tokens", 0)

    def ask(self, *, model: str, system: str, prompt: str, schema: dict) -> dict:
        groq_model = self._models.get(model) or self._models["opus"]
        request = {"model": groq_model, "reasoning_effort": EFFORT.get(model, "medium"),
                   "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}
        answer, why = None, None
        for strict_mode in (True, False):
            body = request | {"response_format": {"type": "json_schema", "json_schema": {
                "name": "answer", "strict": strict_mode, "schema": strict(schema) if strict_mode else schema}}}
            status, reply = self._call(body)
            if status == 400 and strict_mode:
                continue  # a schema strict mode won't take; best effort, checked below
            if status != 200:
                raise ClaudeError(f"Groq said HTTP {status}: {_said(reply)}")
            answer, why = _answer(reply, schema)
            if why is None:
                break
        if why is not None:
            raise ClaudeError(f"Groq's answer doesn't fit the schema: {why}")
        trace.event("claude", block="ask", model=model, backend="groq", groq_model=groq_model, answer=answer)
        return answer

    def _call(self, body: dict) -> tuple[int, dict]:
        """One POST, retried through a short 429, a 5xx or a dropped connection. Raises SetupError on a
        refused key and UsageLimitHit on a 429 that asks for a long wait."""
        data = json.dumps(body).encode()
        headers = HEADERS | {"Authorization": f"Bearer {self._key}"}
        waits = list(TRANSIENT_WAITS)
        while True:
            try:
                status, reply_headers, raw = self._post(URL, data, headers)
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                if not waits:
                    raise ClaudeError(f"Groq can't be reached: {e}") from None
                self._sleep(waits.pop(0))
                continue
            reply = _json(raw)
            if status in (401, 403):
                raise SetupError(BAD_KEY.format(status))
            if status == 429:
                after = _retry_after(reply_headers)
                if after > LONGEST_WAIT or not waits:
                    raise UsageLimitHit(self._now() + timedelta(seconds=after))
                waits.pop(0)
                self._sleep(after)
                continue
            if status >= 500 and waits:
                self._sleep(waits.pop(0))
                continue
            if status == 200:
                used = int((reply.get("usage") or {}).get("total_tokens") or 0)
                self._spent.tokens = getattr(self._spent, "tokens", 0) + used
            return status, reply


def strict(schema: dict) -> dict:
    """`schema` as Groq's strict mode takes it: every object closed with every property required, and each
    property the schema didn't require nullable."""
    schema = dict(schema)
    if schema.get("type") == "object" or "properties" in schema:
        required = set(schema.get("required") or [])
        properties = {}
        for name, sub in (schema.get("properties") or {}).items():
            sub = strict(sub)
            properties[name] = sub if name in required else _nullable(sub)
        schema |= {"properties": properties, "required": list(properties), "additionalProperties": False}
    if isinstance(schema.get("items"), dict):
        schema["items"] = strict(schema["items"])
    return schema


def _nullable(schema: dict) -> dict:
    kind = schema.get("type")
    if isinstance(kind, str):
        schema = schema | {"type": [kind, "null"]}
    elif isinstance(kind, list):
        schema = schema | {"type": [*kind, "null"] if "null" not in kind else kind}
    else:
        return {"anyOf": [schema, {"type": "null"}]}
    if "enum" in schema and None not in schema["enum"]:
        schema["enum"] = [*schema["enum"], None]
    return schema


def _answer(reply: dict, schema: dict) -> tuple[dict | None, str | None]:
    """The answer in a reply, with strict mode's nulls for unrequired properties dropped, and why it doesn't
    fit `schema` (None when it does)."""
    try:
        content = reply["choices"][0]["message"]["content"]
        answer = json.loads(content)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        return None, "no JSON answer in the reply"
    answer = _without_nulls(answer, schema)
    return answer, _misfit(answer, schema)


def _without_nulls(value, schema: dict):
    if isinstance(value, dict) and isinstance(schema.get("properties"), dict):
        required = set(schema.get("required") or [])
        return {k: _without_nulls(v, schema["properties"].get(k) or {}) for k, v in value.items()
                if v is not None or k in required}
    if isinstance(value, list) and isinstance(schema.get("items"), dict):
        return [_without_nulls(v, schema["items"]) for v in value]
    return value


TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def _misfit(value, schema: dict, at: str = "the answer") -> str | None:
    """Why `value` doesn't fit `schema` (its types, required properties, enums and items), or None."""
    kinds = schema.get("type")
    kinds = [kinds] if isinstance(kinds, str) else kinds or []
    if kinds and not any(_is(value, kind) for kind in kinds):
        return f"{at} isn't {' or '.join(kinds)}"
    if "enum" in schema and value not in schema["enum"]:
        return f"{at} isn't one of {schema['enum']}"
    if isinstance(value, dict):
        missing = [k for k in schema.get("required") or [] if k not in value]
        if missing:
            return f"{at} has no {', '.join(missing)}"
        for name, sub in (schema.get("properties") or {}).items():
            if name in value and (why := _misfit(value[name], sub, f"{at}.{name}")):
                return why
    if isinstance(value, list) and isinstance(schema.get("items"), dict):
        for i, item in enumerate(value):
            if why := _misfit(item, schema["items"], f"{at}[{i}]"):
                return why
    return None


def _is(value, kind: str) -> bool:
    if kind == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "number":
        return isinstance(value, int | float) and not isinstance(value, bool)
    return isinstance(value, TYPES.get(kind, object))


def _json(raw: bytes) -> dict:
    try:
        found = json.loads(raw or b"{}")
    except ValueError:
        return {}
    return found if isinstance(found, dict) else {}


def _said(reply: dict) -> str:
    """Groq's error message, one line, without the organization's id (it lands in Records and Traces)."""
    error = reply.get("error")
    message = error.get("message") if isinstance(error, dict) else error
    return re.sub(r"org_[A-Za-z0-9]+", "org_…", " ".join(str(message or "no message").split()))[:300]


def _retry_after(headers: dict) -> float:
    for name, value in headers.items():
        if name.lower() == "retry-after":
            try:
                return max(float(value), 1.0)
            except ValueError:
                break
    return 60.0
