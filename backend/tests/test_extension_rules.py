"""
The Rules table's routes (KAN-756, routers/extension_rules.py), against real
Postgres: a signed-in account asks a site token for a posting's link, and
the token fetches that one job system's table, watermarked for the account,
logged, and capped per account a day. A small table in the engine's shape
stands in for the submodule's.
"""

import datetime
import uuid

import httpx
import pytest
from sqlalchemy import text

from app.config import get_settings
from app.deps import get_current_account
from app.main import app
from app.queries.rules import fetched_by
from app.schemas.auth import AccountType, AuthenticatedAccount
from app.services import rules_table
from app.services.rules_watermark import trace, watermark

pytestmark = pytest.mark.anyio

GREENHOUSE = "https://job-boards.greenhouse.io/acme/jobs/123"
TABLE = {
    "version": 1,
    "answers": [{"pattern": {"source": "^first name$"}, "value": "fact", "args": ["identity.legal_first_name"]}],
    "systems": {
        "greenhouse": {"strings": {"PLACE_US": "United States"}, "patterns": {"DIAL_CODE": {"source": r"\s+\+\d+$"}}},
        "workday": {"strings": {"INTRO": "h3, h4, h5, [data-automation-id=richText], p", "REVIEW": "Review"}},
    },
}


@pytest.fixture
async def accounts(database, monkeypatch):
    """Two accounts with auth.users rows; `as_(i)` signs one in and answers its id."""
    ids = [uuid.uuid4(), uuid.uuid4()]
    async with database() as session:
        for account_id in ids:
            await session.execute(text("INSERT INTO auth.users (id) VALUES (:id)"), {"id": account_id})
        await session.commit()
    monkeypatch.setattr(rules_table, "_table", TABLE)

    def as_(i: int) -> uuid.UUID:
        app.dependency_overrides[get_current_account] = lambda: AuthenticatedAccount(
            id=ids[i], email=f"s{i}@example.com", full_name="Test", account_type=AccountType.APPLICANT, onboarding_completed=True,
        )
        return ids[i]

    yield as_
    app.dependency_overrides.pop(get_current_account, None)


def _api() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost:8000")


async def _token(url: str = GREENHOUSE) -> httpx.Response:
    async with _api() as api:
        return await api.post("/extension/rules/token", json={"url": url})


async def _rules(token: str | None) -> httpx.Response:
    async with _api() as api:
        return await api.get("/extension/rules", headers={"X-WorkIt-Site-Token": token} if token else {})


async def test_a_site_token_fetches_its_job_systems_table_watermarked_for_the_account(accounts, database):
    me = accounts(0)
    got = await _token()
    assert got.status_code == 200, got.text
    body = got.json()
    assert body["job_system"] == "greenhouse" and body["expires_in"] == 300
    assert datetime.datetime.fromisoformat(body["expires_at"]) > datetime.datetime.now(datetime.UTC)
    assert got.headers["cache-control"] == "no-store"

    rules = await _rules(body["token"])
    assert rules.status_code == 200, rules.text
    assert rules.headers["cache-control"] == "no-store"
    # The answer rules and only the token's job system, as the engine's loadRules takes it.
    assert rules.json() == watermark(rules_table.for_site("greenhouse"), me)
    assert list(rules.json()["systems"]) == ["greenhouse"]
    # Again within its minutes: retried fetches work, each one logged.
    assert (await _rules(body["token"])).status_code == 200
    async with database() as session:
        log = (await session.execute(text("SELECT account_id, job_system FROM rules_fetches"))).all()
        assert log == [(me, "greenhouse"), (me, "greenhouse")]
        # Only the token's hash is kept.
        assert (await session.scalar(text("SELECT count(*) FROM rules_tokens WHERE token_hash = :t"), {"t": body["token"]})) == 0


async def test_the_job_system_comes_from_the_link_and_unknown_hosts_are_refused(accounts):
    accounts(0)
    got = await _token("https://acme.wd5.myworkdayjobs.com/en-US/careers/job/Intern_R1")
    assert got.json()["job_system"] == "workday"
    for url in ("https://www.linkedin.com/jobs/view/1", "https://example.com/careers/1", "not a link"):
        refused = await _token(url)
        assert refused.status_code == 422 and refused.json()["detail"] == "WorkIt doesn't fill this site.", url
    # A job system the engine's table has no data for is refused too (lever is on hosts.py, not in TABLE).
    assert (await _token("https://jobs.lever.co/acme/1")).status_code == 422


async def test_a_token_works_only_for_its_account_and_only_until_it_expires(accounts, database):
    accounts(0)
    token = (await _token()).json()["token"]
    accounts(1)
    assert (await _rules(token)).status_code == 401
    assert (await _rules(None)).status_code == 401
    assert (await _rules("made-up")).status_code == 401
    accounts(0)
    async with database() as session:
        await session.execute(text("UPDATE rules_tokens SET expires_at = now() - interval '1 second'"))
        await session.commit()
    expired = await _rules(token)
    assert expired.status_code == 401 and "expired" in expired.json()["detail"]


async def test_signed_out_gets_no_token_and_no_table(accounts):
    accounts(0)
    app.dependency_overrides.pop(get_current_account)
    assert (await _token()).status_code in (401, 403)
    assert (await _rules("anything")).status_code in (401, 403)


async def test_each_call_is_capped_per_account_a_day(accounts, monkeypatch):
    monkeypatch.setattr(get_settings(), "rules_token_daily_cap", 2)
    monkeypatch.setattr(get_settings(), "rules_fetch_daily_cap", 1)
    accounts(0)
    tokens = [(await _token()).json()["token"] for _ in range(2)]
    assert (await _token()).status_code == 429
    assert (await _rules(tokens[0])).status_code == 200
    assert (await _rules(tokens[1])).status_code == 429
    accounts(1)  # another account has its own count
    assert (await _token()).status_code == 200


async def test_without_the_engines_table_both_calls_answer_503(accounts, monkeypatch, tmp_path):
    monkeypatch.setattr(rules_table, "_table", None)
    monkeypatch.setattr(get_settings(), "rules_table_path", tmp_path / "none.json")
    accounts(0)
    assert (await _token()).status_code == 503
    assert (await _rules("anything")).status_code == 503


async def test_the_fetch_log_and_watermark_name_the_account_a_leaked_table_was_served_to(accounts, database):
    for i in (0, 1):
        accounts(i)
        await _rules((await _token("https://acme.wd5.myworkdayjobs.com/job/1")).json()["token"])
    leaker = accounts(1)
    leaked = (await _rules((await _token("https://acme.wd5.myworkdayjobs.com/job/2")).json()["token"])).json()
    async with database() as session:
        candidates = await fetched_by(session, sorted(leaked["systems"]))
    assert len(candidates) == 2
    found = trace(leaked, candidates)
    assert found is not None and found.account_id == leaker and found.decoy
