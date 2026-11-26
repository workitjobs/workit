"""
WorkIt Auto Apply's Send report (D26, KAN-837, routers/apply_reports.py), the window's support form: a student's
report is stored, with or without an Application, only an admin reads it, with the student's email for a reply,
and deleting it once its problem is fixed removes it, since a report has no retention period. A report outside the
shape is refused before anything is stored.
"""
import base64
import uuid

import httpx
import pytest
from sqlalchemy import text

from app.config import get_settings
from app.deps import get_current_account
from app.main import app
from app.routers import apply_reports
from app.schemas.auth import AccountType, AuthenticatedAccount

pytestmark = pytest.mark.anyio

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
REPORT = {
    "category": "answer", "contact_ok": True,
    "application_id": "harvey-123", "company": "Harvey", "role": "Software Engineer Intern",
    "posting_url": "https://jobs.ashbyhq.com/harvey/123", "outcome": "held", "note": "The essay box stayed empty.",
    "files": {"answers.json": '[{"question": "Why Harvey?", "planned": "...", "on_page": ""}]'},
    "screenshots": {"form.png": base64.b64encode(PNG).decode()},
    "trace": '{"t": 0, "kind": "start", "email": "<email>"}\n',
}


def _as(account_id: uuid.UUID, email: str) -> None:
    app.dependency_overrides[get_current_account] = lambda: AuthenticatedAccount(
        id=account_id, email=email, full_name="Someone", account_type=AccountType.APPLICANT, onboarding_completed=True,
    )


@pytest.fixture
async def people(database, monkeypatch):
    ids = {"sam": uuid.uuid4(), "admin": uuid.uuid4()}
    async with database() as session:
        for name, account_id in ids.items():
            await session.execute(text("INSERT INTO auth.users (id) VALUES (:id)"), {"id": account_id})
            await session.execute(text("INSERT INTO applicant_profiles (id, email, full_name) VALUES (:id, :email, :name)"),
                                  {"id": account_id, "email": f"{name}@example.com", "name": name})
        await session.commit()
    monkeypatch.setattr(get_settings(), "workit_admins", "admin@example.com")
    yield ids
    app.dependency_overrides.pop(get_current_account, None)


def _api() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost:8000")


async def test_a_report_is_read_only_by_an_admin_and_goes_once_its_problem_is_fixed(people):
    async with _api() as api:
        _as(people["sam"], "sam@example.com")
        sent = await api.post("/apply-app/reports", json=REPORT)
        assert sent.status_code == 201
        report = sent.json()["id"]
        assert (await api.get("/admin/apply-reports")).status_code == 403

        _as(people["admin"], "admin@example.com")
        [listed] = (await api.get("/admin/apply-reports")).json()["reports"]
        assert (listed["id"], listed["company"], listed["outcome"]) == (report, "Harvey", "held")
        assert (listed["category"], listed["contact_ok"], listed["email"]) == ("answer", True, "sam@example.com")
        whole = (await api.get(f"/admin/apply-reports/{report}")).json()
        assert whole["files"] == REPORT["files"] and whole["trace"] == REPORT["trace"]
        assert whole["screenshots"] == ["form.png"]
        assert (await api.get(f"/admin/apply-reports/{report}/screenshots/form.png")).content == PNG

        assert (await api.delete(f"/admin/apply-reports/{report}")).status_code == 204
        assert (await api.get(f"/admin/apply-reports/{report}")).status_code == 404


async def test_a_general_question_names_no_application(people):
    async with _api() as api:
        _as(people["sam"], "sam@example.com")
        asked = {"category": "app", "note": "How do I change my Worker count?"}
        report = (await api.post("/apply-app/reports", json=asked)).json()["id"]
        _as(people["admin"], "admin@example.com")
        whole = (await api.get(f"/admin/apply-reports/{report}")).json()
        assert (whole["category"], whole["application_id"], whole["files"], whole["trace"]) == ("app", "", {}, "")


async def test_a_report_outside_the_shape_is_refused_and_nothing_is_stored(people, monkeypatch):
    async with _api() as api:
        _as(people["sam"], "sam@example.com")
        for refused in ({**REPORT, "files": {"applicant-profile.yaml": "identity: ..."}},
                        {**REPORT, "screenshots": {"form.png": base64.b64encode(b"not a png").decode()}},
                        {**REPORT, "posting_url": "javascript:alert(1)"},
                        {**REPORT, "category": "billing"}, {**REPORT, "note": ""},
                        {**REPORT, "password": "hunter2"}):
            assert (await api.post("/apply-app/reports", json=refused)).status_code == 422, refused
        monkeypatch.setattr(apply_reports, "BODY_MAX", 100)
        assert (await api.post("/apply-app/reports", json=REPORT)).status_code == 413
        _as(people["admin"], "admin@example.com")
        assert (await api.get("/admin/apply-reports")).json()["total"] == 0
