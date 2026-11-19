"""
The scraper's health for admins (KAN-879): GET /admin/scrape-health counts
boards (failing, resting, stale), board reads per day per hiring system with
their mean time and new jobs, and lists failing boards with their last error.
"""

import datetime
import uuid

import httpx
import pytest
from sqlalchemy import text

from app.config import get_settings
from app.deps import get_current_account
from app.main import app
from app.queries import scrape_health
from app.schemas.auth import AccountType, AuthenticatedAccount

pytestmark = pytest.mark.anyio

ADMIN = "dev@example.com"
NOW = datetime.datetime.now(datetime.UTC).replace(microsecond=0)


def _as(email: str) -> None:
    app.dependency_overrides[get_current_account] = lambda: AuthenticatedAccount(
        id=uuid.uuid4(), email=email, full_name="Test", account_type=AccountType.APPLICANT, onboarding_completed=True,
    )


async def _board(session, ats, token, *, failures=0, last_read=NOW, rest_until=None, enabled=True) -> uuid.UUID:
    return (await session.execute(text(
        "INSERT INTO scraper_schedules (ats, token, company, enabled, last_read_at, consecutive_failures, rest_until)"
        " VALUES (:ats, :token, :token, :enabled, :last_read, :failures, :rest) RETURNING id"
    ), {"ats": ats, "token": token, "enabled": enabled, "last_read": last_read, "failures": failures,
        "rest": rest_until})).scalar_one()


async def _task(session, schedule_id, status, *, seconds=10, error=None, at=NOW) -> None:
    await session.execute(text(
        "INSERT INTO scraper_tasks (schedule_id, status, started_at, finished_at, error)"
        " VALUES (:s, :status, :start, :at, :error)"
    ), {"s": schedule_id, "status": status, "start": at - datetime.timedelta(seconds=seconds), "at": at,
        "error": error})


async def test_scrape_health_counts_boards_reads_and_failures_for_admins_only(database, monkeypatch):
    monkeypatch.setattr(get_settings(), "workit_admins", ADMIN)
    scrape_health.forget()
    async with database() as s:
        good = await _board(s, "greenhouse", "acme")
        bad = await _board(s, "greenhouse", "broken", failures=3,
                           rest_until=NOW + datetime.timedelta(hours=1))
        await _board(s, "lever", "old", last_read=NOW - datetime.timedelta(days=3))
        await _board(s, "lever", "off", enabled=False, failures=9)  # disabled: counted nowhere
        await _task(s, good, "done", seconds=10)
        await _task(s, good, "done", seconds=20)
        await _task(s, bad, "failed", error="HTTP 404", at=NOW - datetime.timedelta(minutes=5))
        await _task(s, bad, "failed", error="HTTP 500")
        await _task(s, good, "done", at=NOW - datetime.timedelta(days=30))  # outside the window
        await s.execute(text("INSERT INTO scraper_tasks (schedule_id) VALUES (:s), (:s)"), {"s": bad})  # the backlog
        await s.execute(text("INSERT INTO job_sources (schedule_id, apply_url) VALUES (:s, 'https://a/1'), (:s, 'https://a/2')"),
                        {"s": good})
        await s.commit()

    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as api:
            _as("sam@example.com")
            assert (await api.get("/admin/scrape-health")).status_code == 403
            _as(ADMIN)
            answer = (await api.get("/admin/scrape-health?days=7")).json()
            # Kept for 10 minutes: a board added now is not in the next answer.
            async with database() as s:
                await _board(s, "ashby", "late")
                await s.commit()
            assert (await api.get("/admin/scrape-health?days=7")).json() == answer
    finally:
        app.dependency_overrides.pop(get_current_account, None)

    assert answer["last_import_at"] is None and answer["read_at"]
    boards = answer["boards"]
    assert boards.pop("oldest_pending_at") is not None
    assert boards == {"boards": 3, "failing": 1, "resting": 1, "stale": 1, "open_jobs": 0, "pending": 2, "claimed": 0}
    assert [(r["ats"], r["boards"], r["read"]) for r in answer["systems"]] == [("greenhouse", 2, 2), ("lever", 1, 1)]
    today = {r["ats"]: r for r in answer["days"] if r["day"] == NOW.date().isoformat()}
    assert today["greenhouse"]["done"] == 2
    assert today["greenhouse"]["failed"] == 2
    assert today["greenhouse"]["mean_seconds"] == pytest.approx(15)
    assert today["greenhouse"]["new_jobs"] == 2
    assert sum(r["done"] for r in answer["days"]) == 2
    assert [(b["token"], b["consecutive_failures"], b["last_error"]) for b in answer["failing"]] == [
        ("broken", 3, "HTTP 500")
    ]
