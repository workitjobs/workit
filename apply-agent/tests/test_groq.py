"""apply.groq: `ask` on Groq (KAN-723), against a fake HTTPS post; no test reaches Groq."""

import json
import urllib.error
from datetime import datetime, timedelta

import pytest

from apply import doctor, groq
from apply.adapters import SetupError, UsageLimitHit
from apply.claude_cli import ClaudeError
from apply.groq import GroqAsk, live_claude, strict
from apply.keychain import InMemoryKeychain

NOW = datetime(2026, 11, 10, 9, 0)
SCHEMA = {"type": "object", "properties": {"answer": {"type": "string"}, "note": {"type": "string"}},
          "required": ["answer"]}


def reply(content, tokens: int = 120, status: int = 200, headers: dict | None = None):
    body = {"choices": [{"message": {"content": json.dumps(content)}}], "usage": {"total_tokens": tokens}}
    return status, headers or {}, json.dumps(body).encode()


def error(status: int, message: str = "no", headers: dict | None = None):
    return status, headers or {}, json.dumps({"error": {"message": message}}).encode()


class FakePost:
    """Stands in for the HTTPS post: returns the given replies in order (an exception is raised)."""

    def __init__(self, *replies):
        self._replies = list(replies)
        self.calls: list[tuple[str, dict, dict]] = []

    def __call__(self, url: str, body: bytes, headers: dict):
        self.calls.append((url, json.loads(body), headers))
        found = self._replies.pop(0)
        if isinstance(found, Exception):
            raise found
        return found


class FakeClaude:
    """The `claude -p` adapter `drive` and `research` stay on."""

    def __init__(self):
        self.asked: list[str] = []

    def spent(self) -> int:
        return 1000

    def drive(self, **kwargs):
        self.asked.append("drive")
        return "driven"

    def research(self, **kwargs):
        self.asked.append("research")
        return "researched"


def groq_ask(post: FakePost, claude=None, slept: list | None = None) -> GroqAsk:
    return GroqAsk("test-key", claude or FakeClaude(), post=post,
                   sleep=(slept.append if slept is not None else lambda s: None), now=lambda: NOW)


def test_ask_sends_the_mapped_model_and_a_strict_schema_and_returns_the_answer():
    post = FakePost(reply({"answer": "Yes", "note": None}, tokens=300))
    claude = groq_ask(post)

    assert claude.ask(model="opus", system="Be brief.", prompt="Authorized?", schema=SCHEMA) == {"answer": "Yes"}

    url, body, headers = post.calls[0]
    assert url == groq.URL
    assert body["model"] == "openai/gpt-oss-120b"
    assert body["reasoning_effort"] == "medium"
    assert body["messages"] == [{"role": "system", "content": "Be brief."}, {"role": "user", "content": "Authorized?"}]
    sent = body["response_format"]["json_schema"]
    assert sent["strict"] is True
    assert sent["schema"]["required"] == ["answer", "note"]
    assert sent["schema"]["properties"]["note"]["type"] == ["string", "null"]
    assert sent["schema"]["additionalProperties"] is False
    assert headers["Authorization"] == "Bearer test-key"
    assert headers["User-Agent"]
    assert claude.spent() == 1000 + 300


def test_haiku_goes_to_the_small_model_with_low_effort():
    post = FakePost(reply({"answer": "ok"}))
    groq_ask(post).ask(model="haiku", system="s", prompt="p", schema=SCHEMA)
    assert post.calls[0][1]["model"] == "openai/gpt-oss-20b"
    assert post.calls[0][1]["reasoning_effort"] == "low"


def test_a_schema_strict_mode_refuses_is_sent_again_in_best_effort_mode():
    post = FakePost(error(400, "unsupported keyword"), reply({"answer": "Yes"}))
    assert groq_ask(post).ask(model="sonnet", system="s", prompt="p", schema=SCHEMA) == {"answer": "Yes"}
    best_effort = post.calls[1][1]["response_format"]["json_schema"]
    assert best_effort["strict"] is False
    assert best_effort["schema"] == SCHEMA


def test_an_answer_that_never_fits_the_schema_is_an_error():
    post = FakePost(reply({"note": "no answer"}), reply({"answer": 3}))
    with pytest.raises(ClaudeError, match="doesn't fit"):
        groq_ask(post).ask(model="opus", system="s", prompt="p", schema=SCHEMA)
    assert len(post.calls) == 2


def test_a_refused_key_is_a_setup_error():
    with pytest.raises(SetupError, match="console.groq.com/keys"):
        groq_ask(FakePost(error(401))).ask(model="opus", system="s", prompt="p", schema=SCHEMA)


def test_a_short_429_waits_and_a_long_one_is_a_limit_hit():
    slept: list = []
    post = FakePost(error(429, headers={"retry-after": "3"}), reply({"answer": "Yes"}))
    assert groq_ask(post, slept=slept).ask(model="opus", system="s", prompt="p", schema=SCHEMA) == {"answer": "Yes"}
    assert slept == [3.0]

    with pytest.raises(UsageLimitHit) as hit:
        groq_ask(FakePost(error(429, headers={"Retry-After": "7200"}))).ask(model="opus", system="s", prompt="p",
                                                                             schema=SCHEMA)
    assert hit.value.resets_at == NOW + timedelta(hours=2)


def test_a_server_error_and_a_dropped_connection_are_retried_then_an_error():
    slept: list = []
    post = FakePost(error(503), urllib.error.URLError("reset"), reply({"answer": "Yes"}))
    assert groq_ask(post, slept=slept).ask(model="opus", system="s", prompt="p", schema=SCHEMA) == {"answer": "Yes"}
    assert slept == [2, 5]

    with pytest.raises(ClaudeError, match="HTTP 500"):
        groq_ask(FakePost(*[error(500)] * 4)).ask(model="opus", system="s", prompt="p", schema=SCHEMA)


def test_a_request_over_the_minute_limit_is_an_error_without_the_organization_id():
    said = "Request too large for model `openai/gpt-oss-120b` in organization `org_01abc` on tokens per minute"
    with pytest.raises(ClaudeError, match="HTTP 413") as found:
        groq_ask(FakePost(error(413, said))).ask(model="opus", system="s", prompt="p", schema=SCHEMA)
    assert "org_01abc" not in str(found.value)


def test_drive_and_research_stay_on_claude():
    claude = FakeClaude()
    both = groq_ask(FakePost(), claude)
    assert both.drive(page=None) == "driven"
    assert both.research() == "researched"
    assert claude.asked == ["drive", "research"]


def test_strict_closes_nested_objects_and_makes_unrequired_enums_nullable():
    schema = {"type": "object", "properties": {
        "fields": {"type": "array", "items": {"type": "object", "properties": {
            "label": {"type": "string"}, "kind": {"type": "string", "enum": ["text", "select"]}},
            "required": ["label"]}}}}
    item = strict(schema)["properties"]["fields"]
    assert item["type"] == ["array", "null"]
    inner = item["items"]
    assert inner["additionalProperties"] is False
    assert inner["required"] == ["label", "kind"]
    assert inner["properties"]["kind"] == {"type": ["string", "null"], "enum": ["text", "select", None]}
    assert schema["properties"]["fields"]["items"]["required"] == ["label"]  # the caller's schema is unchanged


def test_live_claude_follows_ask_model(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    claude = FakeClaude()
    assert live_claude({}, claude) is claude
    assert live_claude({"ask_model": "claude"}, claude) is claude
    with pytest.raises(SetupError, match="no Groq key"):
        live_claude({"ask_model": "groq"}, claude, keychain=InMemoryKeychain())
    with pytest.raises(SetupError, match="neither claude nor groq"):
        live_claude({"ask_model": "gpt"}, claude)

    found = live_claude({"ask_model": "groq", "groq_models": {"haiku": "openai/gpt-oss-120b"}}, claude,
                        keychain=InMemoryKeychain({groq.GROQ_HOST: "saved-key"}))
    assert isinstance(found, GroqAsk)
    assert found._models["haiku"] == "openai/gpt-oss-120b"
    assert found._models["opus"] == "openai/gpt-oss-120b"
    assert found._key == "saved-key"

    monkeypatch.setenv("GROQ_API_KEY", "env-key")
    assert live_claude({"ask_model": "groq"}, claude, keychain=InMemoryKeychain())._key == "env-key"


class Policies:
    """A profile for doctor's checks: only its policies."""

    def __init__(self, **policies):
        self._policies = policies

    def policy(self, key: str):
        return self._policies.get(key)


def test_doctor_checks_the_groq_key_only_for_ask_model_groq():
    def check(key=None, **policies):
        return doctor._ask_model(doctor.Machine(profile=Policies(**policies), groq_key=lambda: key))

    assert check() == []
    assert check(ask_model="claude") == []
    assert check(ask_model="groq")[0].level == doctor.FAIL
    assert check(ask_model="groq")[0].fix == groq.NO_KEY
    found = check(key="k", ask_model="groq")[0]
    assert found.level == doctor.OK
    assert "k" not in found.detail.split()
