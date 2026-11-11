"""apply.ask_model: `ask` on hosted models (KAN-723), against a fake HTTPS post; no test reaches a provider."""

import json
import urllib.error
from datetime import datetime, timedelta

import pytest

from apply import answering, ask_model, doctor
from apply.adapters import SetupError, UsageLimitHit, lean
from apply.ask_model import PROVIDERS, Endpoint, HostedAsk, live_claude, strict
from apply.claude_cli import ClaudeError
from apply.keychain import InMemoryKeychain

NOW = datetime(2026, 11, 10, 9, 0)
SCHEMA = {"type": "object", "properties": {"answer": {"type": "string"}, "note": {"type": "string"}},
          "required": ["answer"]}
GROQ = Endpoint(PROVIDERS["groq"], "groq-key", PROVIDERS["groq"].models)
GEMINI = Endpoint(PROVIDERS["gemini"], "gemini-key", PROVIDERS["gemini"].models)


def reply(content, tokens: int = 120, status: int = 200, headers: dict | None = None):
    body = {"choices": [{"message": {"content": content if isinstance(content, str) else json.dumps(content)}}],
            "usage": {"total_tokens": tokens}}
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


def hosted(post: FakePost, endpoints=(GROQ,), claude=None, slept: list | None = None) -> HostedAsk:
    return HostedAsk(list(endpoints), claude or FakeClaude(), post=post,
                     sleep=(slept.append if slept is not None else lambda s: None), now=lambda: NOW)


def ask(adapter: HostedAsk, model: str = "opus") -> dict:
    return adapter.ask(model=model, system="Be brief.", prompt="Authorized?", schema=SCHEMA)


def test_groq_gets_the_mapped_model_and_a_strict_schema():
    post = FakePost(reply({"answer": "Yes", "note": None}, tokens=300))
    adapter = hosted(post)

    assert ask(adapter) == {"answer": "Yes"}

    url, body, headers = post.calls[0]
    assert url == PROVIDERS["groq"].url
    assert body["model"] == "openai/gpt-oss-120b"
    assert body["reasoning_effort"] == "medium"
    assert body["messages"] == [{"role": "system", "content": "Be brief."}, {"role": "user", "content": "Authorized?"}]
    sent = body["response_format"]["json_schema"]
    assert sent["strict"] is True
    assert sent["schema"]["required"] == ["answer", "note"]
    assert sent["schema"]["properties"]["note"]["type"] == ["string", "null"]
    assert sent["schema"]["additionalProperties"] is False
    assert headers["Authorization"] == "Bearer groq-key"
    assert headers["User-Agent"]
    assert adapter.spent() == 1000 + 300


def test_haiku_goes_to_the_small_model_with_low_effort():
    post = FakePost(reply({"answer": "ok"}))
    ask(hosted(post), "haiku")
    assert post.calls[0][1]["model"] == "openai/gpt-oss-20b"
    assert post.calls[0][1]["reasoning_effort"] == "low"


def test_a_refused_schema_goes_again_as_given_then_as_plain_json():
    post = FakePost(error(400, "unsupported keyword"), error(400, "unsupported keyword"), reply({"answer": "Yes"}))
    assert ask(hosted(post)) == {"answer": "Yes"}
    assert post.calls[1][1]["response_format"]["json_schema"] == {"name": "answer", "strict": False, "schema": SCHEMA}
    plain = post.calls[2][1]
    assert plain["response_format"] == {"type": "json_object"}
    assert json.dumps(SCHEMA) in plain["messages"][0]["content"]


def test_gemini_starts_with_the_schema_as_given_and_its_fenced_json_is_read():
    post = FakePost(reply('```json\n{"answer": "Yes"}\n```'))
    assert ask(hosted(post, (GEMINI,))) == {"answer": "Yes"}
    body = post.calls[0][1]
    assert body["model"] == "gemini-3.5-flash-lite"
    assert body["response_format"]["json_schema"]["strict"] is False
    assert post.calls[0][2]["Authorization"] == "Bearer gemini-key"


def test_a_request_too_large_for_groq_goes_to_gemini():
    said = "Request too large for model `openai/gpt-oss-120b` in organization `org_01abc` on tokens per minute (TPM)"
    post = FakePost(error(413, said), reply({"answer": "Yes"}))
    assert ask(hosted(post, (GROQ, GEMINI))) == {"answer": "Yes"}
    assert [url for url, _, _ in post.calls] == [PROVIDERS["groq"].url, PROVIDERS["gemini"].url]


def test_too_large_on_the_last_endpoint_is_an_error_without_the_organization_id():
    said = "Request too large for model `openai/gpt-oss-120b` in organization `org_01abc` on tokens per minute"
    with pytest.raises(ClaudeError, match="too large") as found:
        ask(hosted(FakePost(error(413, said))))
    assert "org_01abc" not in str(found.value)


def test_a_429_hands_on_at_once_and_the_last_endpoint_waits_a_short_one():
    slept: list = []
    post = FakePost(error(429, headers={"retry-after": "20"}), error(429, headers={"retry-after": "3"}),
                    reply({"answer": "Yes"}))
    assert ask(hosted(post, (GROQ, GEMINI), slept=slept)) == {"answer": "Yes"}
    assert slept == [3.0]  # Groq's 20 s wasn't waited: Gemini took the call

    with pytest.raises(UsageLimitHit) as hit:
        ask(hosted(FakePost(error(429, headers={"Retry-After": "7200"}))))
    assert hit.value.resets_at == NOW + timedelta(hours=2)


def test_an_answer_that_never_fits_moves_on_then_is_an_error():
    post = FakePost(reply({"note": "no answer"}), reply({"answer": 3}), reply({"answer": []}))
    with pytest.raises(ClaudeError, match="doesn't fit"):
        ask(hosted(post))
    assert len(post.calls) == 3  # strict, as given, plain JSON


def test_a_refused_key_is_a_setup_error_and_never_moves_on():
    with pytest.raises(SetupError, match="console.groq.com/keys"):
        ask(hosted(FakePost(error(401)), (GROQ, GEMINI)))


def test_a_server_error_and_a_dropped_connection_are_retried():
    slept: list = []
    post = FakePost(error(503), urllib.error.URLError("reset"), reply({"answer": "Yes"}))
    assert ask(hosted(post, slept=slept)) == {"answer": "Yes"}
    assert slept == [2, 5]

    with pytest.raises(ClaudeError, match="HTTP 500"):
        ask(hosted(FakePost(*[error(500)] * 4)))


def test_drive_and_research_stay_on_claude_and_the_adapter_is_lean():
    claude = FakeClaude()
    both = hosted(FakePost(), claude=claude)
    assert both.drive(page=None) == "driven"
    assert both.research() == "researched"
    assert claude.asked == ["drive", "research"]
    assert lean(both) and not lean(claude)


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
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    claude = FakeClaude()
    assert live_claude({}, claude) is claude
    assert live_claude({"ask_model": "claude"}, claude) is claude
    with pytest.raises(SetupError, match="no groq key"):
        live_claude({"ask_model": "groq"}, claude, keychain=InMemoryKeychain())
    with pytest.raises(SetupError, match="gpt"):
        live_claude({"ask_model": ["groq", "gpt"]}, claude)

    keys = InMemoryKeychain({"api.groq.com": "saved-groq", "generativelanguage.googleapis.com": "saved-gemini"})
    found = live_claude({"ask_model": ["groq", "gemini"], "ask_models": {"groq": {"haiku": "openai/gpt-oss-120b"}}},
                        claude, keychain=keys)
    assert isinstance(found, HostedAsk)
    groq, gemini = found._endpoints
    assert (groq.provider.name, groq.key, groq.models["haiku"]) == ("groq", "saved-groq", "openai/gpt-oss-120b")
    assert (gemini.provider.name, gemini.key) == ("gemini", "saved-gemini")

    monkeypatch.setenv("GEMINI_API_KEY", "env-key")
    assert live_claude({"ask_model": "gemini"}, claude, keychain=InMemoryKeychain())._endpoints[0].key == "env-key"


class Policies:
    """A profile for doctor's checks: only its policies."""

    def __init__(self, **policies):
        self._policies = policies

    def policy(self, key: str):
        return self._policies.get(key)


def test_doctor_checks_each_providers_key_only_when_ask_model_names_one():
    def check(keys=(), **policies):
        machine = doctor.Machine(profile=Policies(**policies), ask_key=lambda name: "k" if name in keys else None)
        return doctor._ask_model(machine)

    assert check() == []
    assert check(ask_model="claude") == []
    assert check(ask_model="gpt")[0].level == doctor.FAIL
    missing = check(("groq",), ask_model=["groq", "gemini"])[0]
    assert missing.level == doctor.FAIL
    assert missing.fix == ask_model.no_key(PROVIDERS["gemini"])
    found = check(("groq", "gemini"), ask_model=["groq", "gemini"])[0]
    assert found.level == doctor.OK
    assert "groq, then gemini" in found.detail


def test_lean_guides_and_rules_keep_their_checks_and_drop_the_examples():
    for kind in answering.load():
        full, short = answering.guide_text([kind]), answering.guide_text([kind], lean=True)
        assert "## Rules" in short and "## Order" in short
        assert "## Pairs" not in short and "## What the reader is checking" not in short
        assert len(short) < len(full)
    rules = answering.rules(lean=True)
    assert "1. **The answer is in the first sentence.**" in rules
    assert "## Length" in rules and "## Types" not in rules
    assert len(rules) < len(answering.rules()) / 2
