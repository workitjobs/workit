"""
WorkIt Auto Apply's Model route (KAN-723, routers/apply_app.py) on the
real-Postgres test database, with ScriptedLLM as the model: a call answers
through the size its tier names and counts its tokens, the student's
identity never reaches the model, the per-minute limit and the monthly Usage
cap refuse a call before it is sent, and a failed call still counts what it
spent. The model call itself (moving down the chain, the schema check) is
tested in ../scout/tests/test_scout.py.
"""

import datetime
import uuid

import httpx
import pytest
from openai import APIStatusError, RateLimitError
from sqlalchemy import text
from workit_scout.testing import ScriptedLLM

from app.config import get_settings
from app.deps import get_current_account
from app.main import app
from app.queries.model_usage import resets_at
from app.schemas.auth import AccountType, AuthenticatedAccount
from app.services.models import get_large_llm, get_small_llm
from tests import fake_models

pytestmark = pytest.mark.anyio

NOW = datetime.datetime(2026, 11, 13, 10, 0, 30, tzinfo=datetime.UTC)
CHOICE = {"type": "object", "properties": {"choice": {"type": ["integer", "null"]}}, "required": ["choice"]}
CALL = {"kind": "pick", "model": "sonnet", "system": "Pick one.", "prompt": "Which group?", "schema": CHOICE}
ANSWER = '{"choice": 1}'
# ScriptedLLM spends a token a character: the prompt's read, the reply's written.
COST = len("Pick one.") + len("Which group?") + len(ANSWER)
_REQUEST = httpx.Request("POST", "http://endpoint.test/v1/chat/completions")


def _account(account_type: AccountType = AccountType.APPLICANT) -> AuthenticatedAccount:
    return AuthenticatedAccount(id=uuid.uuid4(), email="sam@example.com", full_name="Sam Seeker",
                                account_type=account_type, onboarding_completed=True)


@pytest.fixture
async def student(database, monkeypatch):
    account = _account()
    async with database() as session:
        await session.execute(text("INSERT INTO auth.users (id) VALUES (:id)"), {"id": account.id})
        await session.execute(
            text("INSERT INTO applicant_profiles (id, email, full_name, phone_number)"
                 " VALUES (:id, :email, :name, '631-555-0142')"),
            {"id": account.id, "email": account.email, "name": account.full_name},
        )
        await session.commit()
    app.dependency_overrides[get_current_account] = lambda: account
    monkeypatch.setattr("app.routers.apply_app._now", lambda: NOW)
    yield account
    app.dependency_overrides.pop(get_current_account, None)
    fake_models.clear()


def _api() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost:8000")


async def _row(database, account) -> dict | None:
    async with database() as session:
        found = await session.execute(
            text("SELECT input_tokens, output_tokens, calls FROM model_usage WHERE applicant_id = :id"),
            {"id": account.id},
        )
        row = found.mappings().first()
    return dict(row) if row else None


async def test_a_call_answers_and_counts_its_tokens(student, database):
    fake_models.use(ScriptedLLM([ANSWER]))
    async with _api() as api:
        first = await api.post("/apply-app/model", json=CALL)
        assert first.status_code == 200, first.text
        assert first.json() == {
            "answer": {"choice": 1},
            "tokens": COST,
            "usage": {"used": COST, "cap": 3_000_000, "resets_at": "2026-12-01T00:00:00Z"},
        }
        assert (await api.post("/apply-app/model", json=CALL)).json()["usage"]["used"] == 2 * COST
        assert (await api.get("/apply-app/usage")).json()["used"] == 2 * COST
    assert await _row(database, student) == {
        "input_tokens": 2 * (COST - len(ANSWER)), "output_tokens": 2 * len(ANSWER), "calls": 2}


async def test_contact_details_reach_the_model_as_placeholders_and_come_back_as_values(student):
    # The model writes placeholders; the route puts the student's values back.
    fake = ScriptedLLM(['{"note": "Write to [email] or call [phone]."}'])
    fake_models.use(fake)
    note = {"type": "object", "properties": {"note": {"type": "string"}}, "required": ["note"]}
    prompt = "Sam Seeker (sam@example.com, 631 555 0142) asks: which group?"
    async with _api() as api:
        reply = await api.post("/apply-app/model", json={**CALL, "prompt": prompt, "schema": note})
    assert reply.json()["answer"] == {"note": "Write to sam@example.com or call 631 555 0142."}
    # The name stays: the app replaces it (D8), so the prompt keeps its words.
    assert fake.prompts[0][1]["content"] == "Sam Seeker ([email], [phone]) asks: which group?"


async def test_haiku_asks_the_small_chain_and_the_others_the_large(student):
    small, large = ScriptedLLM([ANSWER]), ScriptedLLM([ANSWER])
    app.dependency_overrides[get_small_llm] = lambda: small
    app.dependency_overrides[get_large_llm] = lambda: large
    async with _api() as api:
        for model in ("haiku", "sonnet", "opus"):
            assert (await api.post("/apply-app/model", json={**CALL, "model": model})).status_code == 200
    assert (len(small.prompts), len(large.prompts)) == (1, 2)


async def test_at_the_cap_nothing_reaches_the_model_until_the_first(student, monkeypatch):
    monkeypatch.setattr(get_settings(), "apply_app_monthly_tokens", COST)
    fake = ScriptedLLM([ANSWER])
    fake_models.use(fake)
    async with _api() as api:
        assert (await api.post("/apply-app/model", json=CALL)).status_code == 200
        refused = await api.post("/apply-app/model", json=CALL)
        usage = (await api.get("/apply-app/usage")).json()
    assert refused.status_code == 429
    assert refused.json()["detail"] == "Monthly model use reached; resets on December 1."
    assert int(refused.headers["Retry-After"]) == (resets_at(NOW) - NOW).total_seconds()
    assert len(fake.prompts) == 1
    assert usage == {"used": COST, "cap": COST, "resets_at": "2026-12-01T00:00:00Z"}


async def test_past_the_minute_limit_a_call_waits_for_the_next_minute(student, monkeypatch):
    monkeypatch.setattr(get_settings(), "apply_app_calls_per_minute", 2)
    fake = ScriptedLLM([ANSWER])
    fake_models.use(fake)
    async with _api() as api:
        for _ in range(2):
            assert (await api.post("/apply-app/model", json=CALL)).status_code == 200
        refused = await api.post("/apply-app/model", json=CALL)
        assert refused.status_code == 429
        assert refused.headers["Retry-After"] == "30"
        assert len(fake.prompts) == 2

        monkeypatch.setattr("app.routers.apply_app._now", lambda: NOW + datetime.timedelta(minutes=1))
        assert (await api.post("/apply-app/model", json=CALL)).status_code == 200


@pytest.mark.parametrize(("script", "status"), [
    (["{}"], 502),
    (RateLimitError("quota", response=httpx.Response(429, request=_REQUEST), body=None), 503),
    (APIStatusError("Request too large", response=httpx.Response(413, request=_REQUEST), body=None), 413),
])
async def test_a_failed_call_still_counts_what_it_spent(student, database, script, status):
    fake_models.use(ScriptedLLM(script))
    async with _api() as api:
        failed = await api.post("/apply-app/model", json=CALL)
    assert failed.status_code == status
    assert (failed.headers.get("Retry-After") == "60") is (status == 503)
    spent = len("Pick one.") + len("Which group?") + 2 if status == 502 else 0
    row = await _row(database, student)
    assert (row["input_tokens"] + row["output_tokens"], row["calls"]) == (spent, 1)


@pytest.mark.parametrize("schema", [
    {"type": "array", "items": {"type": "string"}},
    {"type": "object", "properties": {"x": {"$ref": "http://169.254.169.254/x"}}},
    # Python's backtracking `re` would run it on the answer, in the event loop.
    {"type": "object", "properties": {"x": {"type": "string", "pattern": "^(a+)+$"}}},
    {"type": "object", "default": [[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[[]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]]},
    {"type": "object", "properties": {"x": {"type": "number-ish"}}},
    {"type": "object", "description": "x" * 20_001},
])
async def test_a_schema_outside_the_rules_is_refused_before_anything_counts(student, database, schema):
    fake = ScriptedLLM([ANSWER])
    fake_models.use(fake)
    async with _api() as api:
        assert (await api.post("/apply-app/model", json={**CALL, "schema": schema})).status_code == 422
    assert fake.prompts == []
    assert await _row(database, student) is None


async def test_a_company_account_is_refused(database):
    app.dependency_overrides[get_current_account] = lambda: _account(AccountType.COMPANY)
    try:
        async with _api() as api:
            assert (await api.post("/apply-app/model", json=CALL)).status_code == 403
            assert (await api.get("/apply-app/usage")).status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_account, None)


def test_the_cap_resets_on_the_first_of_the_next_month_utc():
    assert resets_at(datetime.datetime(2026, 12, 31, 23, 59, tzinfo=datetime.UTC)) == (
        datetime.datetime(2027, 1, 1, tzinfo=datetime.UTC))
