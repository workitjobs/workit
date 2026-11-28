"""
The reading log (KAN-898, models/resume_readings.py): every reading of an
upload adds one row, with the route, the reader, why the parser's reading
was saved, the time and counts, and never the resume's text or a name. The
reasons come from `bank_import.read_resume` and need no database; the rows
are written by `resume_reading.read_upload` with the route's other writes,
so these tests use the `database` fixture (backend/CLAUDE.md, Tests against
real Postgres). conftest's `_model_down` makes the model unreachable unless
a test installs its own.
"""

import asyncio
import datetime
import json
import uuid

import httpx
import pytest
from openai import APIConnectionError, RateLimitError
from sqlalchemy import text
from workit_scout.identity import Identity
from workit_scout.testing import ScriptedLLM

from app.deps import get_current_account
from app.main import app
from app.models.resume_readings import PARSER_REASONS, ROUTES
from app.queries.resume_readings import readings_by_day
from app.schemas.auth import AccountType, AuthenticatedAccount
from app.scripts.reading_report import table
from app.services import bank_import
from tests import fake_models

pytestmark = pytest.mark.anyio

NAME = "Jordan Rivera"

# Made-up resume: the contact block, then sections the parser and the model both read.
TEXT = """\
Jordan Rivera
jordan.rivera@example.com | (555) 555-0123 | Hillcrest, OR
Experience
Lakeside Labs  Jun 2025 - Aug 2025
Data Intern  Hillcrest, OR
•Cleaned survey records in Python
•Charted weekly results for the Signal Lab team
Education
Hillcrest University  Expected May 2099
B.S. in Statistics
Skills
•Tools: Python, Tableau
"""

READING = {
    "entries": [
        {
            "section": "experience", "title": "Data Intern", "organization": "Lakeside Labs",
            "location": "Hillcrest, OR", "start_month": "2025-06", "end_month": "2025-08", "end_kind": "month",
            "bullets": [
                "Cleaned survey records in Python",
                # Not on the resume: the check drops it
                "Trained a neural network on satellite images",
            ],
        },
        {"section": "education", "title": "Hillcrest University", "degree": "B.S.", "field_of_study": "Statistics"},
    ],
    # Rust is not on the resume: the check drops it
    "skills": [{"name": "Python", "group": "Languages"}, {"name": "Rust", "group": "Languages"}],
}

# Nothing in it is on the resume
UNBACKED = {"entries": [{"section": "experience", "title": "Pilot", "organization": "Northwind Air",
                         "bullets": ["Flew cargo routes"]}], "skills": []}

COLUMNS = {"id", "applicant_id", "created_at", "route", "read_by", "reason", "duration_ms", "entries", "skills",
           "fields_dropped", "model", "input_tokens", "output_tokens"}
# The names ScriptedLLM gives its endpoints, in chain order (workit_scout.testing)
MODELS = ("model-0", "model-1")


def _rate_limited() -> RateLimitError:
    request = httpx.Request("POST", "http://endpoint.test/v1/chat/completions")
    return RateLimitError("quota", response=httpx.Response(429, request=request), body=None)


def _down() -> APIConnectionError:
    return APIConnectionError(request=httpx.Request("POST", "http://model.test/v1"))


# --- the reason each reading gives, no database ----------------------------------


@pytest.mark.parametrize(("script", "reason"), [
    (lambda: _down(), "model_unavailable"),
    (lambda: _rate_limited(), "model_unavailable"),
    (lambda: ["not json"], "wrong_shape"),
    (lambda: [json.dumps(UNBACKED)], "nothing_backed"),
], ids=["down", "out of quota", "wrong shape", "nothing backed"])
async def test_a_failed_model_reading_names_its_reason_and_saves_the_parsers(script, reason):
    parsed = await bank_import.read_resume(TEXT)
    reading = await bank_import.read_resume(TEXT, ScriptedLLM(script()), Identity(name=NAME))
    assert (reading.read_by, reading.reason) == ("parser", reason)
    # What it saves is the parser's reading, as before
    assert (reading.entries, reading.skills) == (parsed.entries, parsed.skills)


async def test_a_reply_the_text_backs_none_of_counts_its_dropped_fields():
    reading = await bank_import.read_resume(TEXT, ScriptedLLM([json.dumps(UNBACKED)]), Identity(name=NAME))
    # Its title, organization and one bullet
    assert (reading.reason, reading.fields_dropped) == ("nothing_backed", 3)


async def test_no_text_and_no_reading_left_need_no_model():
    assert (await bank_import.read_resume("")).reason == "no_text"
    # Text but no model: the caller had no AI reading left today
    reading = await bank_import.read_resume(TEXT)
    assert (reading.read_by, reading.reason, reading.fields_dropped) == ("parser", "no_uses_left", None)


async def test_a_model_slower_than_the_wait_is_a_timeout(monkeypatch):
    async def slow(raw_text, llm, *, identity, answered=None):
        await asyncio.sleep(5)

    monkeypatch.setattr(bank_import, "read_with_model", slow)
    monkeypatch.setattr(bank_import, "MODEL_WAIT_SECONDS", 0.01)
    reading = await bank_import.read_resume(TEXT, ScriptedLLM(["{}"]), Identity(name=NAME))
    assert (reading.read_by, reading.reason) == ("parser", "timeout")
    assert (reading.model, reading.input_tokens, reading.output_tokens) == (None, None, None)


async def test_a_model_reading_counts_the_fields_the_text_does_not_back():
    reading = await bank_import.read_resume(TEXT, ScriptedLLM([json.dumps(READING)]), Identity(name=NAME))
    # The made-up bullet and Rust
    assert (reading.read_by, reading.reason, reading.fields_dropped) == ("model", None, 2)
    assert "Trained a neural network on satellite images" not in [b for e in reading.entries for b in e.bullets]
    assert "Rust" not in [name for name, _ in reading.skills]


# --- the model that replied and its tokens (KAN-955), no database ------------------


async def test_a_model_reading_names_the_model_that_replied_and_its_tokens():
    reply = json.dumps(READING)
    # The first model is out of quota, so the second one reads
    reading = await bank_import.read_resume(TEXT, ScriptedLLM(_rate_limited(), [reply]), Identity(name=NAME))
    assert (reading.read_by, reading.model) == ("model", MODELS[1])
    # ScriptedLLM costs a token a character: the prompt read, the reply written
    assert reading.input_tokens > len(bank_import.MODEL_PROMPT)
    assert reading.output_tokens == len(reply)


@pytest.mark.parametrize(("reply", "reason"), [
    ("not json", "wrong_shape"),
    (json.dumps(UNBACKED), "nothing_backed"),
], ids=["wrong shape", "nothing backed"])
async def test_a_reply_that_is_not_saved_still_names_its_model_and_tokens(reply, reason):
    # The reply was paid for, so the log counts it
    reading = await bank_import.read_resume(TEXT, ScriptedLLM([reply]), Identity(name=NAME))
    assert (reading.read_by, reading.reason) == ("parser", reason)
    assert (reading.model, reading.output_tokens) == (MODELS[0], len(reply))
    assert reading.input_tokens > 0


@pytest.mark.parametrize("script", [lambda: _down(), lambda: _rate_limited()], ids=["down", "out of quota"])
async def test_a_reading_no_model_replied_to_names_no_model(script):
    reading = await bank_import.read_resume(TEXT, ScriptedLLM(script()), Identity(name=NAME))
    assert (reading.model, reading.input_tokens, reading.output_tokens) == (None, None, None)
    # And so does one that asked no model
    reading = await bank_import.read_resume(TEXT)
    assert (reading.model, reading.input_tokens, reading.output_tokens) == (None, None, None)


# --- the rows, on real Postgres ---------------------------------------------------


class _Bucket:
    """The Resume bucket, in memory."""

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.storage = self

    def from_(self, bucket):
        return self

    def upload(self, path, contents, options):
        self.files[path] = contents

    def remove(self, paths):
        for path in paths:
            self.files.pop(path, None)


@pytest.fixture
async def student(database, monkeypatch):
    """A signed-in applicant named Jordan Rivera, an API client and an
    in-memory bucket. Yields (client, applicant id)."""
    applicant_id = uuid.uuid4()
    async with database() as s:
        await s.execute(text("INSERT INTO auth.users (id) VALUES (:id)"), {"id": applicant_id})
        await s.execute(
            text("INSERT INTO applicant_profiles (id, email, full_name) VALUES (:id, :email, :name)"),
            {"id": applicant_id, "email": "jordan.rivera@example.com", "name": NAME},
        )
        await s.commit()
    app.dependency_overrides[get_current_account] = lambda: AuthenticatedAccount(
        id=applicant_id, email="jordan.rivera@example.com", full_name=NAME,
        account_type=AccountType.APPLICANT, onboarding_completed=True,
    )
    bucket = _Bucket()
    monkeypatch.setattr("app.routers.resumes.get_supabase", lambda: bucket)

    async def extract(contents, ext):
        return TEXT

    monkeypatch.setattr("app.routers.resumes._extract", extract)
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            yield client, applicant_id
    finally:
        app.dependency_overrides.pop(get_current_account, None)
        fake_models.clear()


def _file() -> dict:
    return {"file": ("resume.pdf", b"%PDF-1.4 not really a pdf", "application/pdf")}


async def _rows(database) -> list[dict]:
    async with database() as s:
        result = await s.execute(text("SELECT * FROM resume_readings ORDER BY created_at, route"))
        return [dict(row) for row in result.mappings()]


async def test_upload_preview_update_and_import_again_each_log_one_reading(student, database):
    client, applicant_id = student
    resumes = f"/applicants/{applicant_id}/resumes"

    preview = await client.post(f"{resumes}/preview", files=_file())
    assert preview.status_code == 200
    first = await client.post(resumes, files=_file())
    assert first.status_code == 200
    resume_id = first.json()["id"]
    assert (await client.put(f"{resumes}/{resume_id}", files=_file())).status_code == 200
    again = await client.post(f"/applicants/{applicant_id}/bank/import", json={"resume_id": resume_id})
    assert again.status_code == 200

    rows = await _rows(database)
    assert [r["route"] for r in rows] == ["preview", "upload", "update", "import_again"]
    for row in rows:
        # The model is down in tests: each asked it and saved the parser's reading
        assert (row["applicant_id"], row["read_by"], row["reason"]) == (applicant_id, "parser", "model_unavailable")
        assert row["fields_dropped"] is None
        assert row["duration_ms"] >= 0
    found = first.json()["bank"]["found"]
    assert rows[1]["entries"] + rows[1]["skills"] == found


async def test_a_confirmed_preview_logs_no_second_reading(student, database):
    client, applicant_id = student
    resumes = f"/applicants/{applicant_id}/resumes"
    preview = (await client.post(f"{resumes}/preview", files=_file())).json()
    reading = json.dumps({"entries": preview["entries"], "skills": preview["skills"], "read_by": preview["read_by"]})

    res = await client.post(resumes, files=_file(), params={"replace": "matching"}, data={"reading": reading})
    assert res.status_code == 200
    assert [r["route"] for r in await _rows(database)] == ["preview"]


async def test_a_model_reading_is_logged_and_the_next_one_says_none_was_left(student, database):
    client, applicant_id = student
    fake_models.use(ScriptedLLM([json.dumps(READING)]))
    resumes = f"/applicants/{applicant_id}/resumes"

    first = await client.post(resumes, files=_file())
    assert first.json()["bank"]["read_by"] == "model"
    resume_id = first.json()["id"]
    await client.post(f"/applicants/{applicant_id}/bank/import", json={"resume_id": resume_id})

    model, parser = await _rows(database)
    assert (model["read_by"], model["reason"], model["fields_dropped"]) == ("model", None, 2)
    assert model["entries"] + model["skills"] == first.json()["bank"]["found"]
    assert (parser["route"], parser["read_by"], parser["reason"]) == ("import_again", "parser", "no_uses_left")
    # KAN-955: the model that replied and its tokens; none where no model was asked
    assert model["model"] == MODELS[0]
    assert model["input_tokens"] > 0 and model["output_tokens"] == len(json.dumps(READING))
    assert (parser["model"], parser["input_tokens"], parser["output_tokens"]) == (None, None, None)


async def test_a_model_name_longer_than_its_column_never_fails_the_upload(student, database):
    from workit_scout.settings import Endpoint

    from app.models.resume_readings import MODEL_NAME_LENGTH

    client, applicant_id = student
    fake = ScriptedLLM([json.dumps(READING)])
    long = Endpoint("http://endpoint0.test/v1", "m" * (MODEL_NAME_LENGTH + 50))
    fake._scripts = {long: fake._scripts[fake._endpoints[0][0]]}
    fake._endpoints = [(long, fake._endpoints[0][1])]
    fake_models.use(fake)

    res = await client.post(f"/applicants/{applicant_id}/resumes", files=_file())
    assert res.status_code == 200, res.text
    assert [r["model"] for r in await _rows(database)] == ["m" * MODEL_NAME_LENGTH]


async def test_the_log_keeps_no_resume_text_or_name(student, database):
    client, applicant_id = student
    fake_models.use(ScriptedLLM([json.dumps(READING)]))
    await client.post(f"/applicants/{applicant_id}/resumes", files=_file())
    await client.post(f"/applicants/{applicant_id}/resumes/preview", files=_file())

    rows = await _rows(database)
    assert len(rows) == 2
    for row in rows:
        # A new column is a new place text could go: add it here once checked
        assert set(row) == COLUMNS
        # Every text column holds one of the code's own words, never the resume's
        for column, value in row.items():
            if isinstance(value, str):
                assert value in {*ROUTES, "model", "parser", *PARSER_REASONS, *MODELS}, column
        for said in (NAME, "Rivera", "Lakeside", "Hillcrest", "555-0123", "Cleaned survey records"):
            assert said not in str(row)


async def test_a_failed_save_logs_nothing(student, database, monkeypatch):
    client, applicant_id = student

    async def broken(*args, **kwargs):
        raise RuntimeError("the database went away")

    monkeypatch.setattr("app.routers.resumes.bank.import_upload", broken)
    res = await client.post(f"/applicants/{applicant_id}/resumes", files=_file())
    assert res.status_code == 500
    assert await _rows(database) == []


async def test_the_log_goes_with_the_account(student, database):
    client, applicant_id = student
    await client.post(f"/applicants/{applicant_id}/resumes/preview", files=_file())
    assert len(await _rows(database)) == 1

    async with database() as s:
        await s.execute(text("DELETE FROM auth.users WHERE id = :id"), {"id": applicant_id})
        await s.commit()
    assert await _rows(database) == []


# --- the admin report ---------------------------------------------------------


async def test_the_report_counts_readings_by_day_reader_and_reason(database):
    now = datetime.datetime(2026, 11, 16, 15, 0, tzinfo=datetime.UTC)
    applicant_id = uuid.uuid4()
    async with database() as s:
        await s.execute(text("INSERT INTO auth.users (id) VALUES (:id)"), {"id": applicant_id})
        await s.execute(
            text("INSERT INTO applicant_profiles (id, email, full_name) VALUES (:id, 'jr@example.com', :name)"),
            {"id": applicant_id, "name": NAME},
        )
        for at, read_by, reason, ms, dropped in (
            (now, "model", None, 4000, 2),
            (now, "model", None, 6000, 0),
            (now, "parser", "timeout", 45000, None),
            (now - datetime.timedelta(days=1), "parser", "no_uses_left", 100, None),
            # Past the period asked for
            (now - datetime.timedelta(days=20), "parser", "wrong_shape", 3000, None),
        ):
            await s.execute(
                text(
                    "INSERT INTO resume_readings (applicant_id, created_at, route, read_by, reason, duration_ms,"
                    " entries, skills, fields_dropped)"
                    " VALUES (:a, :at, 'upload', :by, :reason, :ms, 3, 2, :dropped)"
                ),
                {"a": applicant_id, "at": at, "by": read_by, "reason": reason, "ms": ms, "dropped": dropped},
            )
        await s.commit()

    async with database() as s:
        rows = await readings_by_day(s, days=14, now=now)
    today, yesterday = now.date(), now.date() - datetime.timedelta(days=1)
    assert rows == [
        {"day": today, "read_by": "model", "reason": None, "readings": 2, "seconds": 5.0, "fields_dropped": 1.0},
        {"day": today, "read_by": "parser", "reason": "timeout", "readings": 1, "seconds": 45.0,
         "fields_dropped": None},
        {"day": yesterday, "read_by": "parser", "reason": "no_uses_left", "readings": 1, "seconds": 0.1,
         "fields_dropped": None},
    ]
    lines = table(rows).splitlines()
    assert lines[0].split() == ["day", "read_by", "reason", "readings", "seconds", "fields_dropped"]
    assert lines[1].split() == [str(today), "model", "-", "2", "5.0", "1.0"]
    assert table([]) == "No readings in that period."
