"""Hosted models in place of `claude -p` for `ask` (KAN-723, ../docs/desktop_application_auto_apply.md §8).

policies.yaml's `ask_model` names the backend of every `ask` (answers, essays, edits, checks): a provider in
PROVIDERS (`groq`, `gemini`), a list of them tried in order (`[groq, gemini]`, the default since 2026-11-10:
Gemini takes a call Groq refuses as too large, rate-limits or can't answer), or `claude` (`claude -p` on a
developer's own login, set in their policies.yaml). `drive` and
`research` stay on `claude -p`. Apply's model names map to each provider's (`Provider.models`, overridden key
by key by `ask_models.<provider>`). Each key is the provider's environment variable, else Keychain, else the
checkout's root .env (Scout's endpoints); a developer's key for testing, never one shipped in an app: the
launched desktop app calls hosted models only, through a WorkIt route that holds the keys (§8).

A hosted adapter is lean (apply.adapters.lean): the essay prompts shrink to fit a free tier's request limit
(Groq's 8,000 tokens a minute, seen 2026-11-10).

Groq's strict JSON schema mode needs every property `required` and every object closed, so `strict` rewrites
a schema: a property the schema didn't require becomes nullable, and its null is dropped from the answer,
which then has the shape `claude -p` gives. A schema a mode refuses (HTTP 400) goes again in the next mode:
strict (Groq only), then the schema as given, then plain JSON with the schema in the system prompt. Every
answer is checked against the schema (`_misfit`) before it returns.
"""

import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit

from apply import trace
from apply.adapters import SetupError, UsageLimitHit
from apply.claude_cli import ClaudeCLI, ClaudeError
from apply.home import CODE
from apply.keychain import GEMINI, GEMINI_HOST, GROQ, GROQ_HOST, MacKeychain


@dataclass(frozen=True)
class Provider:
    """An OpenAI-compatible chat API that `ask` can use."""

    name: str
    url: str  # its chat completions endpoint
    models: dict[str, str]  # Apply's model names (claude -p's) to its own
    effort: dict[str, str] = field(default_factory=dict)  # reasoning_effort by Apply's model name; "*" for the rest
    strict: bool = False  # it takes strict JSON schemas (with every property required and every object closed)
    env: str = ""  # the environment variable its key may be in
    keychain: tuple[str, str] = ("", "")  # the Keychain item its key may be in: (service, account)
    keys_page: str = ""  # where a developer makes a key


PROVIDERS = {
    # Both gpt-oss models are production models that take strict schemas (console.groq.com/docs/models, read
    # 2026-11-10); Scout runs on the same two. Haiku's jobs are checks (claude_cli._argv gives it --effort low).
    "groq": Provider("groq", "https://api.groq.com/openai/v1/chat/completions",
                     {"opus": "openai/gpt-oss-120b", "sonnet": "openai/gpt-oss-120b", "haiku": "openai/gpt-oss-20b"},
                     {"haiku": "low", "*": "medium"}, strict=True, env="GROQ_API_KEY", keychain=(GROQ, GROQ_HOST),
                     keys_page="console.groq.com/keys"),
    # Scout's Gemini (scout/CLAUDE.md): the free tier reads far more a minute than Groq's.
    "gemini": Provider("gemini", "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
                       dict.fromkeys(("opus", "sonnet", "haiku"), "gemini-3.5-flash-lite"), {"*": "low"},
                       env="GEMINI_API_KEY", keychain=(GEMINI, GEMINI_HOST), keys_page="aistudio.google.com/apikey"),
}


@dataclass(frozen=True)
class Endpoint:
    """A provider with a key and its model names."""

    provider: Provider
    key: str
    models: dict[str, str]


TIMEOUT = 180  # seconds for one reply; an essay takes a few
TRANSIENT_WAITS = (2, 5, 15)  # seconds before each retry of a 5xx, a timeout or a dropped connection
# Seconds: a 429 that asks for longer is a limit hit (UsageLimitHit), not a wait. A tokens-a-minute limit
# (8,000 on Groq's free tier, seen 2026-11-10) always clears within a minute; a daily one asks for hours.
LONGEST_WAIT = 60
HEADERS = {"Content-Type": "application/json", "User-Agent": "workit-apply/0.1"}  # Groq's edge refuses urllib's own
JSON_ONLY = "Reply with one JSON object only, no other text, that fits this JSON schema:\n"

# POSTs (url, body, headers) and returns (status, headers, body); an HTTP error is a status, not a raise.
Post = Callable[[str, bytes, dict], tuple[int, dict, bytes]]


def https_post(url: str, body: bytes, headers: dict) -> tuple[int, dict, bytes]:
    request = urllib.request.Request(url, body, headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as reply:
            return reply.status, dict(reply.headers), reply.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read()


# The checkout's root .env (a developer's, copied by `npm run worktree`): Scout's endpoints there hold the team's
# Groq and Gemini keys, so a developer needs no key of their own. A packaged app has none, and calls through WorkIt.
DOTENV = CODE.parent / ".env"
SCOUT_LISTS = ("SCOUT_ENDPOINTS_LARGE", "SCOUT_ENDPOINTS", "SCOUT_ENDPOINTS_SMALL")


def no_key(provider: Provider) -> str:
    service, account = provider.keychain
    return (f"no {provider.name} key: copy the team's .env into the checkout's root (Scout's SCOUT_ENDPOINTS hold it), "
            f"set {provider.env}, or save it in Keychain with `security add-generic-password -s {service} -a {account} "
            "-w` (it asks for the key); a developer can set ask_model: claude in policies.yaml instead")


def key(provider: Provider, keychain=None, dotenv: Path = DOTENV) -> str | None:
    """`provider`'s API key: its environment variable, else its Keychain item, else the checkout's .env (Scout's
    endpoint on the provider's host); None with none of them."""
    service, account = provider.keychain
    return (os.environ.get(provider.env) or (keychain or MacKeychain(service)).password(account)
            or _from_dotenv(provider, dotenv))


def _from_dotenv(provider: Provider, path: Path) -> str | None:
    """The key in `path` of a Scout endpoint on `provider`'s host: an entry of SCOUT_ENDPOINTS (or its _LARGE and
    _SMALL), else SCOUT_API_KEY when SCOUT_BASE_URL is that host. Nothing else in the file is read."""
    if not path.is_file():
        return None
    host = urlsplit(provider.url).hostname
    values = {}
    for line in path.read_text().splitlines():
        name, sep, value = line.partition("=")
        if sep and not name.lstrip().startswith("#"):
            values[name.strip()] = value.strip().strip("'\"")
    for name in SCOUT_LISTS:
        try:
            entries = json.loads(values.get(name) or "[]")
        except ValueError:
            continue
        for entry in entries if isinstance(entries, list) else []:
            if isinstance(entry, dict) and entry.get("api_key") and urlsplit(str(entry.get("base_url") or "")).hostname == host:
                return str(entry["api_key"])
    if values.get("SCOUT_API_KEY") and urlsplit(values.get("SCOUT_BASE_URL") or "").hostname == host:
        return values["SCOUT_API_KEY"]
    return None


def chain(policies: dict) -> list[str]:
    """The providers policies.yaml's ask_model names, in order; [] for claude. policies.default.yaml names
    [groq, gemini] (2026-11-10, KAN-723); policies with no ask_model key (a test's) read as claude. Raises
    SetupError on a name that is neither claude nor a provider."""
    named = policies.get("ask_model") or "claude"
    names = [named] if isinstance(named, str) else list(named)
    if names == ["claude"]:
        return []
    if wrong := [n for n in names if n not in PROVIDERS]:
        raise SetupError(f"ask_model names {', '.join(map(str, wrong))}: use claude, or one or more of "
                         f"{', '.join(PROVIDERS)}")
    return names


def live_claude(policies: dict, claude: ClaudeCLI | None = None, keychain=None, dotenv: Path = DOTENV):
    """The Claude adapter policies.yaml's ask_model names: `claude` itself, or a HostedAsk over its providers."""
    claude = claude or ClaudeCLI()
    if not (names := chain(policies)):
        return claude
    overrides = policies.get("ask_models") or {}
    endpoints = []
    for name in names:
        provider = PROVIDERS[name]
        if not (found := key(provider, keychain, dotenv)):
            raise SetupError(no_key(provider))
        endpoints.append(Endpoint(provider, found, provider.models | (overrides.get(name) or {})))
    return HostedAsk(endpoints, claude)


class _Next(Exception):
    """This endpoint can't take the call now (too large, rate-limited, down, or its answer never fit): try the
    next one; with none left, `error` is raised."""

    def __init__(self, error: Exception):
        super().__init__(str(error))
        self.error = error


class HostedAsk:
    """The Claude adapter with `ask` on hosted models, tried in order. `drive`, `research` and anything else go to
    `claude`; `spent` counts both."""

    lean = True  # apply.adapters.lean: the essay prompts shrink to fit a free tier

    def __init__(self, endpoints: list[Endpoint], claude: ClaudeCLI, post: Post = https_post,
                 sleep: Callable[[float], None] = time.sleep, now: Callable[[], datetime] = datetime.now):
        self._endpoints = endpoints
        self._claude = claude
        self._post = post
        self._sleep = sleep
        self._now = now
        self._spent = threading.local()  # tokens used by each thread's calls, as ClaudeCLI keeps them

    def __getattr__(self, name: str):
        return getattr(self._claude, name)

    def spent(self) -> int:
        return self._claude.spent() + getattr(self._spent, "tokens", 0)

    def ask(self, *, model: str, system: str, prompt: str, schema: dict) -> dict:
        error: Exception = ClaudeError("no ask_model endpoint")
        for i, endpoint in enumerate(self._endpoints):
            try:
                return self._ask(endpoint, model, system, prompt, schema, last=i == len(self._endpoints) - 1)
            except _Next as moved:
                error = moved.error
                trace.event("claude", block="ask", model=model, backend=endpoint.provider.name, moved_on=str(error))
        raise error

    def _ask(self, endpoint: Endpoint, model: str, system: str, prompt: str, schema: dict, last: bool) -> dict:
        provider = endpoint.provider
        name = endpoint.models.get(model) or endpoint.models["opus"]
        effort = provider.effort.get(model) or provider.effort.get("*")
        messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        request = {"model": name, "messages": messages} | ({"reasoning_effort": effort} if effort else {})
        modes = [*(["strict"] if provider.strict else []), "schema", "json"]
        why = "no answer"
        for mode in modes:
            if mode == "json":
                body = request | {"response_format": {"type": "json_object"}, "messages": [
                    {"role": "system", "content": f"{system}\n\n{JSON_ONLY}{json.dumps(schema)}"}, messages[1]]}
            else:
                body = request | {"response_format": {"type": "json_schema", "json_schema": {
                    "name": "answer", "strict": mode == "strict",
                    "schema": strict(schema) if mode == "strict" else schema}}}
            status, reply = self._call(endpoint, body, last)
            if status == 400 and mode != modes[-1] and not _too_large(reply):
                continue  # a schema this mode won't take: the next mode
            if status == 413 or _too_large(reply):
                raise _Next(ClaudeError(f"{provider.name} said the request is too large: {_said(reply)}"))
            if status != 200:
                raise ClaudeError(f"{provider.name} said HTTP {status}: {_said(reply)}")
            answer, why = _answer(reply, schema)
            if why is None:
                trace.event("claude", block="ask", model=model, backend=provider.name, provider_model=name,
                            answer=answer)
                return answer
        raise _Next(ClaudeError(f"{provider.name}'s answer doesn't fit the schema: {why}"))

    def _call(self, endpoint: Endpoint, body: dict, last: bool) -> tuple[int, dict]:
        """One POST, retried through a 5xx or a dropped connection, and through a short 429 on the last endpoint
        (an earlier one hands the call on at once). Raises SetupError on a refused key."""
        provider = endpoint.provider
        data = json.dumps(body).encode()
        headers = HEADERS | {"Authorization": f"Bearer {endpoint.key}"}
        waits = list(TRANSIENT_WAITS)
        while True:
            try:
                status, reply_headers, raw = self._post(provider.url, data, headers)
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                if not waits:
                    raise _Next(ClaudeError(f"{provider.name} can't be reached: {e}")) from None
                self._sleep(waits.pop(0))
                continue
            reply = _json(raw)
            if status in (401, 403):
                raise SetupError(f"{provider.name} refused the key (HTTP {status}): make a new one at "
                                 f"{provider.keys_page} and save it again")
            if status == 429:
                after = _retry_after(reply_headers)
                if not last or after > LONGEST_WAIT or not waits:
                    raise _Next(UsageLimitHit(self._now() + timedelta(seconds=after)))
                waits.pop(0)
                self._sleep(after)
                continue
            if status >= 500:
                if not waits:
                    raise _Next(ClaudeError(f"{provider.name} said HTTP {status}: {_said(reply)}"))
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
        content = reply["choices"][0]["message"]["content"].strip()
        answer = json.loads(re.sub(r"^```(?:json)?\s*|\s*```$", "", content))
    except (KeyError, IndexError, TypeError, AttributeError, json.JSONDecodeError):
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
    if isinstance(found, list) and found and isinstance(found[0], dict):  # Gemini wraps some errors in a list
        found = found[0]
    return found if isinstance(found, dict) else {}


def _too_large(reply: dict) -> bool:
    """Whether an error reply says the request is over the model's context or a per-minute token limit."""
    return bool(re.search(r"too large|context length|context window|maximum context|token count", _said(reply),
                          re.IGNORECASE)) and "error" in reply


def _said(reply: dict) -> str:
    """The provider's error message, one line, without the organization's id (it lands in Records and Traces)."""
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
