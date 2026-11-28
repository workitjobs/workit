"""
Resume reading for admins (KAN-953): GET /admin/resume-reading counts the
reading log's rows for a period (per day by reader, by reason, by model with
tokens and their paid cost), today's AI readings against the day's limit, the
newest readings and the newest recorded scoring run. Admins only.
"""

import datetime
import json
import uuid

import httpx
import pytest
from sqlalchemy import text

from app.config import Settings, get_settings
from app.deps import get_current_account
from app.main import app
from app.queries.resume_readings import _cost
from app.routers.resume_reading import ScoringRun
from app.schemas.auth import AccountType, AuthenticatedAccount
from app.services import reading_scores

pytestmark = pytest.mark.anyio

ADMIN = "dev@example.com"
NOW = datetime.datetime.now(datetime.UTC).replace(microsecond=0)
# Earlier than NOW and on the same UTC day, so a day's counts hold just after midnight.
EARLIER = NOW.replace(hour=0, minute=0, second=0)
GEMINI, GPT = "gemini-3.5-flash-lite", "openai/gpt-oss-20b"


# --- no database ------------------------------------------------------------------


def test_a_models_tokens_cost_its_paid_price_and_an_unpriced_model_costs_nothing_shown():
    prices = {GEMINI: (0.10, 0.40)}
    # 2,000,000 read at $0.10 a million and 500,000 written at $0.40
    assert _cost(prices, GEMINI, 2_000_000, 500_000) == 0.4
    assert _cost(prices, GPT, 2_000_000, 500_000) is None
    assert _cost(prices, None, 10, 10) is None


@pytest.mark.parametrize(("value", "prices"), [
    ('{"gemini-3.5-flash-lite": [0.1, 0.4]}', {GEMINI: (0.1, 0.4)}),
    ("", {}),
    ("not json", {}),
    ('{"gemini-3.5-flash-lite": 0.1}', {}),
    ('["gemini-3.5-flash-lite"]', {}),
], ids=["set", "unset", "not json", "no pair", "no map"])
def test_model_prices_parse_or_are_no_prices(value, prices):
    # A wrong value is no prices, never an error: the page still loads
    assert Settings.model_construct(model_prices=value).prices == prices


def test_the_newest_recorded_scoring_run_is_the_last_one(tmp_path):
    path = tmp_path / "scores.json"
    run = {"ran": "2026-11-17", "set": "made_up", "resumes": 19, "model": GEMINI,
           "parser": 71.5, "ai": 93.0, "combined": 96.8}
    path.write_text(json.dumps({"runs": [{**run, "ran": "2026-11-01"}, run]}))
    assert reading_scores.last_run(path) == run


@pytest.mark.parametrize("contents", [None, "not json", "{}", '{"runs": []}', '{"runs": 3}'],
                         ids=["missing", "not json", "no runs key", "no run", "not a list"])
def test_a_missing_or_unreadable_record_is_no_run(tmp_path, contents):
    path = tmp_path / "scores.json"
    if contents is not None:
        path.write_text(contents)
    assert reading_scores.last_run(path) is None


def test_the_committed_record_holds_a_run_the_page_can_show():
    # The file the API ships: its newest run fits the route's shape
    assert ScoringRun(**reading_scores.last_run()).combined > 0


# --- the route, on real Postgres --------------------------------------------------


def _as(email: str) -> None:
    app.dependency_overrides[get_current_account] = lambda: AuthenticatedAccount(
        id=uuid.uuid4(), email=email, full_name="Test", account_type=AccountType.APPLICANT, onboarding_completed=True,
    )


async def _student(session) -> uuid.UUID:
    applicant_id = uuid.uuid4()
    await session.execute(text("INSERT INTO auth.users (id) VALUES (:id)"), {"id": applicant_id})
    await session.execute(
        text("INSERT INTO applicant_profiles (id, email, full_name) VALUES (:id, :email, 'Jordan Rivera')"),
        {"id": applicant_id, "email": f"{applicant_id}@example.com"},
    )
    return applicant_id


async def _reading(session, applicant_id, *, at=NOW, read_by="model", reason=None, ms=4000, model=None,
                   read=None, written=None, route="upload") -> None:
    await session.execute(
        text(
            "INSERT INTO resume_readings (applicant_id, created_at, route, read_by, reason, duration_ms,"
            " entries, skills, fields_dropped, model, input_tokens, output_tokens)"
            " VALUES (:a, :at, :route, :by, :reason, :ms, 3, 2, NULL, :model, :read, :written)"
        ),
        {"a": applicant_id, "at": at, "route": route, "by": read_by, "reason": reason, "ms": ms,
         "model": model, "read": read, "written": written},
    )


async def test_resume_reading_counts_the_log_for_admins_only(database, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "workit_admins", ADMIN)
    monkeypatch.setattr(settings, "model_prices", json.dumps({GEMINI: [1.0, 2.0]}))
    yesterday = NOW - datetime.timedelta(days=1)
    async with database() as s:
        student = await _student(s)
        # Today: two model readings, one by each model, and two the parser made
        await _reading(s, student, at=EARLIER, ms=2000, model=GEMINI, read=2000, written=500)
        await _reading(s, student, ms=1000, model=GPT, read=1000, written=400)
        await _reading(s, student, read_by="parser", reason="no_uses_left", ms=100, route="preview")
        # A reply that failed the schema was paid for, so its model and tokens count
        await _reading(s, student, read_by="parser", reason="wrong_shape", ms=3000, model=GEMINI,
                       read=1000, written=500)
        # Yesterday: a model reading from before the log held the model's name, and a timeout
        await _reading(s, student, at=yesterday, ms=6000)
        await _reading(s, student, at=yesterday, read_by="parser", reason="timeout", ms=20000)
        await _reading(s, student, at=yesterday - datetime.timedelta(hours=1), read_by="parser",
                       reason="timeout", ms=20000)
        # Before the period asked for
        await _reading(s, student, at=NOW - datetime.timedelta(days=30), model=GEMINI, read=9, written=9)
        # Every student's AI readings today, and one student's own row, which is not the pool's
        await s.execute(text(
            "INSERT INTO ai_usage_counters (account_id, feature, day, count) VALUES"
            " (NULL, 'parsing', :day, 7), (:a, 'parsing', :day, 1), (NULL, 'tailor', :day, 40)"
        ), {"day": NOW.date(), "a": student})
        await s.commit()

    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as api:
            _as("sam@example.com")
            assert (await api.get("/admin/resume-reading")).status_code == 403
            _as(ADMIN)
            res = await api.get("/admin/resume-reading?days=7")
            assert res.status_code == 200, res.text
            answer = res.json()
            assert (await api.get("/admin/resume-reading?days=91")).status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_account, None)

    assert answer["today"] == {"used": 7, "cap": int(settings.ai_daily_pool * settings.ai_parsing_share)}
    assert answer["days"] == [
        {"day": yesterday.date().isoformat(), "ai": 1, "parser": 2},
        {"day": NOW.date().isoformat(), "ai": 2, "parser": 2},
    ]
    # Most first, then by name
    assert [(r["reason"], r["readings"]) for r in answer["reasons"]] == [
        ("timeout", 2), ("no_uses_left", 1), ("wrong_shape", 1),
    ]
    assert answer["reasons"][0]["last_at"].startswith(yesterday.date().isoformat())
    # The model readings alone: 1 s, 2 s and 6 s
    assert answer["median_seconds"] == 2.0
    by_model = {m["model"]: m for m in answer["models"]}
    assert by_model[GEMINI] == {
        "model": GEMINI, "readings": 2, "median_seconds": 2.5, "input_tokens": 3000, "output_tokens": 1000,
        # 3,000 read at $1 a million and 1,000 written at $2
        "cost": 0.005,
    }
    assert (by_model[GPT]["readings"], by_model[GPT]["cost"]) == (1, None)
    # The reading from before the model's name was logged
    assert (by_model[None]["readings"], by_model[None]["input_tokens"]) == (1, 0)
    assert answer["models"][0]["model"] == GEMINI

    recent = answer["recent"]
    assert len(recent) == 7
    assert [r["at"] for r in recent] == sorted((r["at"] for r in recent), reverse=True)
    newest = next(r for r in recent if r["model"] == GPT)
    assert newest == {
        "at": newest["at"], "account": str(student), "route": "upload", "read_by": "model", "model": GPT,
        "reason": None, "seconds": 1.0, "entries": 3, "skills": 2, "tokens": 1400,
    }
    assert next(r for r in recent if r["reason"] == "no_uses_left")["tokens"] is None
    # Counts, times and ids only: nothing of the student but the account id
    assert "Jordan" not in res.text and "example.com" not in res.text
    assert answer["accuracy"] == reading_scores.last_run()


async def test_resume_reading_with_no_readings_is_empty_not_an_error(database, monkeypatch):
    monkeypatch.setattr(get_settings(), "workit_admins", ADMIN)
    _as(ADMIN)
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as api:
            answer = (await api.get("/admin/resume-reading")).json()
    finally:
        app.dependency_overrides.pop(get_current_account, None)
    assert (answer["days"], answer["reasons"], answer["models"], answer["recent"]) == ([], [], [], [])
    assert (answer["median_seconds"], answer["today"]["used"]) == (None, 0)
