"""
WorkIt Auto Apply's sign-in (KAN-723, W5; app/services/app_sign_in.py) on the
real-Postgres test database, with a fake Supabase: the website's page gets a
code for the app's PKCE challenge, the app trades it with its verifier for a
new session of the student's own, and a code is good once, for 5 minutes, and
only with the verifier its challenge was made from.
"""

import datetime
import types
import uuid

import httpx
import pytest
from sqlalchemy import text

from app.deps import get_current_account
from app.main import app
from app.schemas.auth import AccountType, AuthenticatedAccount
from app.services import app_sign_in

pytestmark = pytest.mark.anyio

NOW = datetime.datetime(2026, 11, 15, 10, 0, tzinfo=datetime.UTC)
VERIFIER = "v" * 43
CHALLENGE = app_sign_in.challenge_of(VERIFIER)
SESSION = {"access_token": "access-1", "refresh_token": "refresh-1", "expires_at": 1_800_000_000,
           "expires_in": 3600, "user": {}}


class FakeSupabase:
    """The admin calls the sign-in makes, recorded; and Auth's /verify, which
    answers SESSION for the token generate_link gave."""

    def __init__(self, email: str):
        self.links: list[dict] = []
        self.auth = types.SimpleNamespace(admin=types.SimpleNamespace(
            get_user_by_id=lambda uid: types.SimpleNamespace(user=types.SimpleNamespace(id=uid, email=email)),
            generate_link=self._link,
        ))

    def _link(self, params: dict):
        self.links.append(params)
        return types.SimpleNamespace(properties=types.SimpleNamespace(hashed_token="hashed-1"))

    async def verify(self, token_hash: str) -> dict | None:
        return SESSION if token_hash == "hashed-1" else None


@pytest.fixture
async def student(database, monkeypatch):
    account = AuthenticatedAccount(id=uuid.uuid4(), email="sam@example.com", full_name="Sam Seeker",
                                   account_type=AccountType.APPLICANT, onboarding_completed=True)
    async with database() as session:
        await session.execute(text("INSERT INTO auth.users (id) VALUES (:id)"), {"id": account.id})
        await session.execute(text("INSERT INTO applicant_profiles (id, email, full_name) VALUES (:id, :email, :name)"),
                              {"id": account.id, "email": account.email, "name": account.full_name})
        await session.commit()
    fake = FakeSupabase(account.email)
    monkeypatch.setattr(app_sign_in, "get_supabase", lambda: fake)
    monkeypatch.setattr(app_sign_in, "_verify", fake.verify)
    monkeypatch.setattr("app.routers.apply_app._now", lambda: NOW)
    app.dependency_overrides[get_current_account] = lambda: account
    yield fake
    app.dependency_overrides.pop(get_current_account, None)


def _api() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost:8000")


async def _code(api: httpx.AsyncClient, challenge: str = CHALLENGE) -> str:
    answer = await api.post("/apply-app/sign-in", json={"challenge": challenge})
    assert answer.status_code == 201, answer.text
    assert answer.json()["expires_in"] == 300
    # A student's page shows no code: only an admin's Developer checkout pastes one.
    assert answer.json()["paste"] is False
    return answer.json()["code"]


async def test_the_app_trades_its_code_once_for_a_session_of_its_own(student):
    async with _api() as api:
        code = await _code(api)
        traded = await api.post("/apply-app/session", json={"code": code, "verifier": VERIFIER})
        assert traded.status_code == 200, traded.text
        assert traded.json() == {"access_token": "access-1", "refresh_token": "refresh-1", "expires_at": 1_800_000_000}
        assert student.links == [{"type": "magiclink", "email": "sam@example.com"}]
        again = await api.post("/apply-app/session", json={"code": code, "verifier": VERIFIER})
        assert again.status_code == 400
    assert len(student.links) == 1


async def test_another_verifier_gets_nothing_and_spends_the_code(student):
    async with _api() as api:
        code = await _code(api)
        wrong = await api.post("/apply-app/session", json={"code": code, "verifier": "w" * 43})
        assert wrong.status_code == 400
        late = await api.post("/apply-app/session", json={"code": code, "verifier": VERIFIER})
        assert late.status_code == 400
    assert student.links == []


async def test_a_code_expires_after_five_minutes(student, monkeypatch):
    async with _api() as api:
        code = await _code(api)
        monkeypatch.setattr("app.routers.apply_app._now", lambda: NOW + datetime.timedelta(minutes=5))
        assert (await api.post("/apply-app/session", json={"code": code, "verifier": VERIFIER})).status_code == 400


async def test_only_an_admin_may_paste_the_code(student, monkeypatch):
    monkeypatch.setattr("app.routers.apply_app.is_admin", lambda account: True)
    async with _api() as api:
        answer = await api.post("/apply-app/sign-in", json={"challenge": CHALLENGE})
    assert answer.json()["paste"] is True


async def test_a_company_account_gets_no_code(student):
    app.dependency_overrides[get_current_account] = lambda: AuthenticatedAccount(
        id=uuid.uuid4(), email="hr@example.com", full_name="HR", account_type=AccountType.COMPANY,
        onboarding_completed=True)
    async with _api() as api:
        assert (await api.post("/apply-app/sign-in", json={"challenge": CHALLENGE})).status_code == 403


async def test_eleven_sign_ins_in_an_hour_wait_for_the_oldest(student, monkeypatch):
    async with _api() as api:
        for minute in range(app_sign_in.PER_HOUR):
            monkeypatch.setattr("app.routers.apply_app._now", lambda m=minute: NOW + datetime.timedelta(minutes=m))
            await _code(api)
        refused = await api.post("/apply-app/sign-in", json={"challenge": CHALLENGE})
        assert refused.status_code == 429
        # The last code was made at minute 9; the oldest, at minute 0, is an hour old at minute 60.
        assert refused.headers["Retry-After"] == str(51 * 60)
        monkeypatch.setattr("app.routers.apply_app._now", lambda: NOW + datetime.timedelta(minutes=60, seconds=1))
        await _code(api)


async def test_supabase_refusing_the_link_is_a_503(student, monkeypatch):
    async def refused(token_hash):
        return None

    monkeypatch.setattr(app_sign_in, "_verify", refused)
    async with _api() as api:
        code = await _code(api)
        assert (await api.post("/apply-app/session", json={"code": code, "verifier": VERIFIER})).status_code == 503
