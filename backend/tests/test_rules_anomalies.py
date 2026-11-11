"""
The admins' look at the Rules table's fetch log (KAN-772): the anomaly
report's four flags on fixture rows (services/rules_anomalies.py `flag`),
GET /admin/rules-anomalies and its script's table against real Postgres,
admins only.
"""

import datetime
import itertools
import uuid

import httpx
import pytest
from sqlalchemy import text

from app.config import Settings, get_settings
from app.deps import get_current_account
from app.main import app
from app.schemas.auth import AccountType, AuthenticatedAccount
from app.scripts import rules_anomalies as anomalies_script
from app.services import rules_table
from app.services.rules_anomalies import flag, table

T0 = datetime.datetime(2026, 11, 10, 9, 0, tzinfo=datetime.UTC)
SETTINGS = Settings(rules_token_daily_cap=400, rules_fetch_daily_cap=400)
SYSTEMS = ["ashby", "greenhouse", "icims", "lever", "workday", "workable", "oracle"]


def _at(minutes: float) -> datetime.datetime:
    return T0 + datetime.timedelta(minutes=minutes)


def _reasons(fetches, counts=()) -> dict[uuid.UUID, list[str]]:
    return {a.account_id: [f.reason for f in a.flags] for a in flag(fetches, counts, SETTINGS)}


# --- The flags, on fixture rows ---

STUDENT = uuid.UUID(int=1)
# A student's day: a dozen postings on two job systems at uneven gaps, each one filled.
STUDENT_DAY = [(STUDENT, ["greenhouse", "workday"][i % 2], _at(m)) for i, m in enumerate([0, 3, 11, 12, 30, 47, 49, 80, 95, 140, 141, 200])]
STUDENT_FILLS = [(STUDENT, "fill_event", T0.date(), 12)]


def test_a_students_day_flags_nothing():
    assert _reasons(STUDENT_DAY, STUDENT_FILLS) == {}


def test_many_job_systems_in_a_short_window_is_flagged():
    walker = uuid.uuid4()
    rows = [(walker, s, _at(i * 4)) for i, s in enumerate(SYSTEMS[:6])]  # six systems in 20 minutes
    slow = uuid.uuid4()
    rows += [(slow, s, _at(i * 60)) for i, s in enumerate(SYSTEMS)]  # seven, an hour apart
    found = flag(rows, [], SETTINGS)
    assert [a.account_id for a in found] == [walker]
    assert found[0].flags[0].reason == "many_systems" and found[0].flags[0].detail == "6 job systems within 30 minutes"


def test_fetching_far_more_than_filling_is_flagged():
    puller = uuid.uuid4()
    # 40 fetches at a person's uneven gaps.
    minutes = itertools.accumulate(itertools.islice(itertools.cycle([1, 4, 9, 2, 15, 6, 30]), 40))
    fetches = [(puller, "greenhouse", _at(m)) for m in minutes]
    assert _reasons(fetches, [(puller, "fill_event", T0.date(), 2)]) == {puller: ["fetch_without_fill"]}
    # The same fetches with as many fills: a student filling all day.
    assert _reasons(fetches, [(puller, "fill_event", T0.date(), 40)]) == {}


def test_fetches_on_a_timer_are_flagged_and_a_persons_scatter_is_not():
    timer = uuid.uuid4()
    rows = [(timer, "greenhouse", _at(i * 2 + (0.05 if i % 3 else 0))) for i in range(25)]
    fills = [(timer, "fill_event", T0.date(), 25)]
    assert _reasons(rows, fills) == {timer: ["regular_timing"]}
    # Too few gaps to say.
    assert _reasons(rows[:10], fills) == {}


def test_reaching_the_daily_cap_on_several_days_is_flagged():
    capped = uuid.uuid4()
    rows = [(capped, "greenhouse", _at(m)) for m in (0, 7, 31)]
    day = T0.date()
    once = [(capped, "rules_fetch", day, 400), (capped, "fill_event", day, 3)]
    assert _reasons(rows, once) == {}
    twice = [*once, (capped, "rules_token", day - datetime.timedelta(days=1), 400)]
    found = flag(rows, twice, SETTINGS)
    assert [f.reason for f in found[0].flags] == ["capped"] and found[0].flags[0].detail == "at the daily cap on 2 days"


def test_the_thresholds_come_from_the_settings():
    walker = uuid.uuid4()
    rows = [(walker, s, _at(i * 4)) for i, s in enumerate(SYSTEMS[:3])]
    assert flag(rows, [], SETTINGS) == []
    assert flag(rows, [], Settings(rules_anomaly_systems=3))[0].flags[0].reason == "many_systems"


# --- The admin route, the script and the leak check, against real Postgres ---

ADMIN = "dev@example.com"
TABLE = {
    "version": 1,
    "answers": [{"pattern": {"source": "^first name$"}, "value": "fact", "args": ["identity.legal_first_name"]}],
    "systems": {"workday": {"strings": {"INTRO": "h3, h4, h5, [data-automation-id=richText], p"}}},
}


@pytest.fixture
async def accounts(database, monkeypatch):
    """A student and an admin (on WORKIT_ADMINS) with auth.users rows; `as_(i)` signs one in (0 student, 1 admin)."""
    ids = [uuid.uuid4(), uuid.uuid4()]
    async with database() as session:
        for account_id in ids:
            await session.execute(text("INSERT INTO auth.users (id) VALUES (:id)"), {"id": account_id})
        await session.commit()
    monkeypatch.setattr(get_settings(), "workit_admins", ADMIN)
    monkeypatch.setattr(rules_table, "_table", TABLE)

    def as_(i: int) -> uuid.UUID:
        app.dependency_overrides[get_current_account] = lambda: AuthenticatedAccount(
            id=ids[i], email=ADMIN if i else "sam@example.com", full_name="Test",
            account_type=AccountType.APPLICANT, onboarding_completed=True,
        )
        return ids[i]

    yield as_
    app.dependency_overrides.pop(get_current_account, None)


async def _log(database, account_id: uuid.UUID, rows: list[tuple[str, datetime.datetime]]) -> None:
    async with database() as session:
        for system, at in rows:
            await session.execute(
                text("INSERT INTO rules_fetches (account_id, job_system, created_at) VALUES (:a, :s, :t)"),
                {"a": account_id, "s": system, "t": at},
            )
        await session.commit()


def _api() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost:8000")


@pytest.mark.anyio
async def test_the_report_is_for_admins_only_and_names_the_flagged_account(accounts, database):
    student = accounts(0)
    now = datetime.datetime.now(datetime.UTC)
    await _log(database, student, [(s, now - datetime.timedelta(minutes=30 - i)) for i, s in enumerate(SYSTEMS)])
    # A fetch older than the window is left out.
    await _log(database, student, [("lever", now - datetime.timedelta(days=9))])
    async with _api() as api:
        refused = await api.get("/admin/rules-anomalies")
        assert refused.status_code == 403
        accounts(1)
        got = await api.get("/admin/rules-anomalies?days=7")
        assert (await api.get("/admin/rules-anomalies?days=91")).status_code == 422
    assert got.status_code == 200, got.text
    body = got.json()
    assert body["days"] == 7
    [flagged] = body["accounts"]
    assert flagged["account_id"] == str(student) and flagged["fetches"] == 7 and flagged["fills"] == 0
    assert [f["reason"] for f in flagged["flags"]] == ["many_systems"]

    # The script's table says the same.
    printed = table(await anomalies_script._report(7))
    assert str(student) in printed and "many_systems: 7 job systems within 30 minutes" in printed
    assert printed.splitlines()[0].split() == ["account", "fetches", "fills", "systems", "last", "fetch", "(UTC)", "flags"]


@pytest.mark.anyio
async def test_an_empty_log_reports_no_account(accounts):
    accounts(1)
    printed = table(await anomalies_script._report(3))
    assert printed == "No account flagged in the last 3 days."

