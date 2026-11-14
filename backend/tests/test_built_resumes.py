"""
Seam-1 tests for Generate (KAN-207): base resumes through the API on real
Postgres. Content is read back from the Word download, which needs no
Tectonic; the PDF render's own tests are in test_resume_render.py, and the
render route's tests below skip without Tectonic (backend/CLAUDE.md, Tests).
"""

import datetime
import json
import uuid

import httpx
import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.deps import get_current_account, token_applicant
from app.main import app
from app.schemas.auth import AccountType, AuthenticatedAccount

pytestmark = pytest.mark.anyio


async def _seed_applicant(session) -> uuid.UUID:
    applicant_id = uuid.uuid4()
    await session.execute(text("INSERT INTO auth.users (id) VALUES (:id)"), {"id": applicant_id})
    await session.execute(
        text(
            "INSERT INTO applicant_profiles (id, email, full_name, phone_number, github_url)"
            " VALUES (:id, :email, 'Sam Seeker', '555-010-2030', 'https://github.com/samseeker')"
        ),
        {"id": applicant_id, "email": f"sam{applicant_id.hex[:6]}@example.com"},
    )
    await session.commit()
    return applicant_id


def _sign_in(applicant_id: uuid.UUID) -> None:
    app.dependency_overrides[get_current_account] = lambda: AuthenticatedAccount(
        id=applicant_id,
        email="sam@example.com",
        full_name="Sam Seeker",
        account_type=AccountType.APPLICANT,
        onboarding_completed=True,
    )

    # The render's token-only check (deps.token_applicant), as the token would
    def token(applicant_id: uuid.UUID) -> uuid.UUID:
        if applicant_id != signed_in:
            raise HTTPException(403, "Forbidden")
        return applicant_id

    signed_in = applicant_id
    app.dependency_overrides[token_applicant] = token


@pytest.fixture
async def student(database):
    """A signed-in applicant and an API client. Yields (client, applicant URL)."""
    async with database() as session:
        applicant_id = await _seed_applicant(session)
    _sign_in(applicant_id)
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, f"/applicants/{applicant_id}"
    finally:
        app.dependency_overrides.pop(get_current_account, None)


async def test_generate_makes_a_base_resume_the_list_reads_back(student):
    client, me = student
    res = await client.post(f"{me}/built-resumes", json={"name": "General SWE"})

    assert res.status_code == 201
    made = res.json()
    assert made["name"] == "General SWE"
    assert made["template"] == "jakes"
    assert made["job_posting_id"] is None
    assert made["is_default"] is True  # the student's only resume

    listed = (await client.get(f"{me}/built-resumes")).json()
    assert [(r["id"], r["name"]) for r in listed] == [(made["id"], "General SWE")]


async def _fill_bank(client, me) -> None:
    """Entries posted out of order, so the resume's order is the bank's."""
    bank = f"{me}/bank"
    for body in (
        {"section": "projects", "title": "WorkIt", "organization": "CSE 416", "start_month": "2026-01",
         "end_kind": "present", "bullets": ["Built a resume builder with FastAPI"]},
        {"section": "experience", "title": "Tutor", "organization": "Campus Center", "location": "Stony Brook, NY",
         "start_month": "2023-09", "end_month": "2024-05", "bullets": ["Tutored 40 students in calculus"]},
        {"section": "experience", "title": "Software Intern", "organization": "Acme", "location": "New York, NY",
         "start_month": "2025-06", "end_month": "2025-08",
         "bullets": ["Cut page load time by 30%", "Wrote the billing service's tests"]},
        {"section": "education", "title": "Stony Brook University", "location": "Stony Brook, NY",
         "degree": "Bachelor of Science", "field_of_study": "Computer Science", "gpa": 3.8, "gpa_scale": 4.0,
         "coursework": ["Data Structures", "Algorithms"], "start_month": "2023-08",
         "end_kind": "expected", "end_month": "2027-05"},
        {"section": "awards", "title": "Dean's List", "organization": "Stony Brook University", "award_date": "2024-12"},
    ):
        assert (await client.post(f"{bank}/entries", json=body)).status_code == 201
    for skill in ({"name": "Python", "group": "Languages"}, {"name": "Docker", "group": "Tools"}):
        assert (await client.post(f"{bank}/skills", json=skill)).status_code == 201


def _docx_lines(content: bytes) -> list[str]:
    from io import BytesIO

    from docx import Document

    return [p.text for p in Document(BytesIO(content)).paragraphs if p.text.strip()]


async def _generate(client, me, name="Base Resume") -> str:
    res = await client.post(f"{me}/built-resumes", json={"name": name})
    assert res.status_code == 201, res.text
    return res.json()["id"]


async def _new_skill(client, me) -> None:
    res = await client.post(f"{me}/bank/skills", json={"name": f"Skill {uuid.uuid4().hex[:8]}"})
    assert res.status_code == 201, res.text


async def _another(client, me, name="Base Resume") -> str:
    """One more resume from the bank. Generate refuses one that prints the
    same as a resume the student has (KAN-267), so the bank gains a skill
    first; nothing else on the resume changes."""
    await _new_skill(client, me)
    return await _generate(client, me, name)


async def test_the_word_file_has_every_entry_in_section_order_newest_first(student):
    client, me = student
    await _fill_bank(client, me)
    resume_id = await _generate(client, me, "General SWE")

    res = await client.get(f"{me}/built-resumes/{resume_id}/docx")
    assert res.status_code == 200
    assert res.headers["content-disposition"] == 'attachment; filename="General SWE.docx"'
    assert _docx_lines(res.content) == [
        "Sam Seeker",
        f"+1 555-010-2030 | sam{me.split('/')[2].replace('-', '')[:6]}@example.com | github.com/samseeker",
        "EDUCATION",
        "Stony Brook University\tStony Brook, NY",
        "Bachelor of Science in Computer Science\tAug. 2023 – Expected May 2027",
        "GPA: 3.8/4.0",
        "Relevant Coursework: Data Structures, Algorithms",
        "EXPERIENCE",
        "Software Intern\tJune 2025 – Aug. 2025",
        "Acme\tNew York, NY",
        "Cut page load time by 30%",
        "Wrote the billing service's tests",
        "Tutor\tSep. 2023 – May 2024",
        "Campus Center\tStony Brook, NY",
        "Tutored 40 students in calculus",
        "PROJECTS",
        "WorkIt | CSE 416\tJan. 2026 – Present",
        "Built a resume builder with FastAPI",
        "AWARDS",
        "Dean's List | Stony Brook University\tDec. 2024",
        "TECHNICAL SKILLS",
        "Languages: Python",
        "Tools: Docker",
    ]


async def test_the_latex_file_is_the_pdfs_source_without_markers(student):
    client, me = student
    await _fill_bank(client, me)
    resume_id = await _generate(client, me, "General SWE")

    res = await client.get(f"{me}/built-resumes/{resume_id}/tex")
    assert res.status_code == 200
    assert res.headers["content-disposition"] == 'attachment; filename="General SWE.tex"'
    tex = res.text
    assert tex.startswith("%") and r"\begin{document}" in tex and tex.rstrip().endswith(r"\end{document}")
    assert r"\scshape Sam Seeker" in tex and "555-010-2030" in tex
    assert r"\section{Experience}" in tex and "Cut page load time by 30\\%" in tex
    assert r"\wimark" not in tex and r"\pdfsavepos" not in tex


async def test_the_header_says_us_citizen_once_the_citizenship_answer_does(student):
    client, me = student
    await _fill_bank(client, me)
    resume_id = await _generate(client, me, "General SWE")
    assert "U.S. Citizen" not in (await client.get(f"{me}/built-resumes/{resume_id}/tex")).text

    res = await client.patch(f"{me}/autofill-answers", json={"work_authorization_status": "us_citizen"})
    assert res.status_code == 200
    assert r"U.S. Citizen $|$ " in (await client.get(f"{me}/built-resumes/{resume_id}/tex")).text


async def test_the_latex_file_is_only_its_owners(student):
    client, me = student
    res = await client.get(f"{me}/built-resumes/{uuid.uuid4()}/tex")
    assert res.status_code == 404


async def test_the_word_file_is_letter_size(student):
    from io import BytesIO

    from docx import Document
    from docx.shared import Inches

    client, me = student
    resume_id = await _generate(client, me)
    section = Document(BytesIO((await client.get(f"{me}/built-resumes/{resume_id}/docx")).content)).sections[0]
    assert (section.page_width, section.page_height) == (Inches(8.5), Inches(11))


async def test_a_bank_fix_shows_but_a_new_entry_waits_off_the_resume(student):
    client, me = student
    await _fill_bank(client, me)
    resume_id = await _generate(client, me)
    bank = (await client.get(f"{me}/bank")).json()
    tutor = next(e for e in bank["entries"] if e["title"] == "Tutor")

    # A typo fixed in the bank shows on the resume (a live view)...
    await client.patch(f"{me}/bank/bullets/{tutor['bullets'][0]['id']}", json={"text": "Tutored 45 students in calculus"})
    # ...but an entry, bullet or skill added after Generate has no choice row.
    await client.post(f"{me}/bank/entries", json={"section": "experience", "title": "Barista", "organization": "Cafe"})
    await client.post(f"{me}/bank/entries/{tutor['id']}/bullets", json={"text": "Ran review sessions"})
    await client.post(f"{me}/bank/skills", json={"name": "Rust", "group": "Languages"})

    lines = _docx_lines((await client.get(f"{me}/built-resumes/{resume_id}/docx")).content)
    assert "Tutored 45 students in calculus" in lines
    assert "Tutored 40 students in calculus" not in lines
    assert not any("Barista" in line or "Rust" in line or "Ran review sessions" in line for line in lines)

    # A resume made now has them all.
    fresh = _docx_lines((await client.get(f"{me}/built-resumes/{await _generate(client, me)}/docx")).content)
    assert "Barista" in fresh and "Ran review sessions" in fresh and "Languages: Python, Rust" in fresh


async def test_generate_leaves_a_copy_of_an_entry_off(student):
    # An import saved "as new" left two of one job in a bank; Generate showed
    # both, and the resume ran to two pages. The copy waits in "Not on This
    # Resume"; a job held twice at one company in other months is two jobs.
    client, me = student
    job = {"section": "experience", "title": "Software Intern", "organization": "Acme",
           "start_month": "2025-06", "end_month": "2025-08", "bullets": ["Cut page load time by 30%"]}
    for body in (job, {**job, "title": "software intern ", "organization": "ACME"},
                 {**job, "start_month": "2024-06", "end_month": "2024-08", "bullets": ["Wrote tests"]}):
        res = await client.post(f"{me}/bank/entries?allow_duplicate=true", json=body)
        assert res.status_code == 201, res.text
    resume_id = await _generate(client, me)

    lines = _docx_lines((await client.get(f"{me}/built-resumes/{resume_id}/docx")).content)
    assert lines.count("Cut page load time by 30%") == 1
    assert "Wrote tests" in lines
    choices = (await client.get(f"{me}/built-resumes/{resume_id}/choices")).json()
    hidden = [e for e in choices["entries"] if not e["shown"]]
    assert len(hidden) == 1


def test_generate_shows_each_skill_name_once():
    # KAN-504: two copies of a name (case and spaces aside) are one skill; the
    # first in the bank's order shows and the rest wait hidden, with rows.
    from types import SimpleNamespace

    from app.services.built_resumes import base_choices

    names = ("Go", "Python", " python", "PYTHON ", "Rust")
    skills = [SimpleNamespace(id=uuid.uuid4(), name=n, group="Languages") for n in names]
    choices = base_choices(SimpleNamespace(entries=[], skills=skills))
    assert [choices.skills[s.id].shown for s in skills] == [True, True, False, False, True]


async def test_generate_shows_a_skill_two_uploads_hold_once(student, monkeypatch):
    # KAN-504: each upload owns its skills (ADR 0005), so two uploads each
    # held Python. Generate showed both, the resume printed it twice, and
    # Fit to One Page then cut both, so Cut From Resume listed it twice.
    monkeypatch.setattr("app.routers.resumes.get_supabase", lambda: _FakeSupabase())
    monkeypatch.setattr("app.routers.resumes._extract", _no_text)
    client, me = student
    uploads = []
    for _ in range(2):
        res = await _upload(client, me)
        assert res.status_code == 200, res.text
        uploads.append(res.json()["id"])
    for upload, name in zip(uploads, ("Python", "PYTHON")):
        res = await client.post(f"{me}/bank/skills?resume_id={upload}", json={"name": name, "group": "Languages"})
        assert res.status_code == 201, res.text
    resume_id = await _generate(client, me)

    lines = _docx_lines((await client.get(f"{me}/built-resumes/{resume_id}/docx")).content)
    assert [line.lower() for line in lines if line.startswith("Languages")] == ["languages: python"]
    choices = (await client.get(f"{me}/built-resumes/{resume_id}/choices")).json()
    assert sorted(s["shown"] for s in choices["skills"]) == [False, True]
    # The copy shown is the one with the lower id, on every read (KAN-444):
    # the bank's order broke the tie at random, so a second Generate could
    # show the other copy and miss that it was a duplicate.
    assert next(s for s in choices["skills"] if s["shown"])["skill_id"] == min(s["skill_id"] for s in choices["skills"])
    res = await client.post(f"{me}/built-resumes", json={})
    assert (res.status_code, res.json()["detail"]["built_resume_id"]) == (409, resume_id)


async def test_generate_refuses_a_resume_the_student_already_has(student):
    """KAN-267: a second Generate with nothing changed made a copy."""
    client, me = student
    await _fill_bank(client, me)
    first = await _generate(client, me, "General SWE")

    res = await client.post(f"{me}/built-resumes", json={})
    assert res.status_code == 409
    assert res.json()["detail"] == {
        "message": "Duplicate Resume found: General SWE", "built_resume_id": first, "name": "General SWE"}
    assert [r["id"] for r in (await client.get(f"{me}/built-resumes")).json()] == [first]

    # The first resume edited, a new one is not the same...
    bullet = next(e for e in (await client.get(f"{me}/bank")).json()["entries"]
                  if e["title"] == "Software Intern")["bullets"][0]["id"]
    await client.patch(f"{me}/built-resumes/{first}/choices",
                       json={"bullets": [{"bullet_id": bullet, "shown": False}]})
    second = await _generate(client, me, "Everything")
    # ...but it is, once more, the one to match.
    res = await client.post(f"{me}/built-resumes", json={})
    assert (res.status_code, res.json()["detail"]["built_resume_id"]) == (409, second)

    # A bank entry added since makes the next one new.
    await client.post(f"{me}/bank/entries", json={"section": "experience", "title": "Barista", "organization": "Cafe"})
    assert (await client.post(f"{me}/built-resumes", json={})).status_code == 201


def _lines(res: httpx.Response) -> list[dict]:
    return [json.loads(line) for line in res.text.splitlines()]


async def test_a_streamed_generate_names_each_step_then_the_resume(student):
    """KAN-444: the Resumes page shows Generate's steps as they happen."""
    client, me = student
    await _fill_bank(client, me)
    res = await client.post(f"{me}/built-resumes/stream", json={})

    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/x-ndjson")
    lines = _lines(res)
    assert lines[:2] == [{"type": "phase", "phase": "checking"}, {"type": "phase", "phase": "saving"}]
    assert [line["type"] for line in lines] == ["phase", "phase", "done"]
    made = lines[-1]["resume"]
    assert (made["name"], made["is_default"]) == ("Resume #1", True)
    # Committed: the list reads it back
    assert [r["id"] for r in (await client.get(f"{me}/built-resumes")).json()] == [made["id"]]


async def test_a_streamed_generate_names_the_duplicate_and_writes_nothing(student):
    client, me = student
    await _fill_bank(client, me)
    first = await _generate(client, me, "General SWE")

    lines = _lines(await client.post(f"{me}/built-resumes/stream", json={}))
    assert lines == [
        {"type": "phase", "phase": "checking"},
        {"type": "error", "status": 409, "message": "Duplicate Resume found: General SWE", "built_resume_id": first,
         "name": "General SWE"},
    ]
    assert [r["id"] for r in (await client.get(f"{me}/built-resumes")).json()] == [first]


async def test_a_confirmed_copy_is_made_without_the_check(student):
    """KAN-444: the Resumes page asks "You Already Have This Resume", and
    the student's Confirm makes the copy, streamed or not."""
    client, me = student
    await _fill_bank(client, me)
    first = await _generate(client, me, "General SWE")

    lines = _lines(await client.post(f"{me}/built-resumes/stream", json={"allow_duplicate": True}))
    assert [line.get("phase", line["type"]) for line in lines] == ["saving", "done"]
    res = await client.post(f"{me}/built-resumes", json={"allow_duplicate": True})
    assert res.status_code == 201
    listed = [r["id"] for r in (await client.get(f"{me}/built-resumes")).json()]
    assert len(listed) == 3 and first in listed


async def test_generate_tells_a_tailored_resume_with_its_own_skill_from_a_new_base_resume(student, database):
    """Generate reads the bank once, every resume's own skills included, and
    leaves those skills off the new resume (KAN-444): a tailored resume
    whose own skill is its only difference is not a duplicate, and the new
    resume does not show that skill."""
    client, me = student
    await _fill_bank(client, me)
    first = await _generate(client, me, "General SWE")
    applicant_id = uuid.UUID(me.rsplit("/", 1)[1])
    skill = uuid.uuid4()
    async with database() as session:
        await session.execute(
            text("INSERT INTO bank_skills (id, applicant_id, name, built_resume_id) VALUES (:id, :a, 'Kubernetes', :r)"),
            {"id": skill, "a": applicant_id, "r": uuid.UUID(first)},
        )
        await session.execute(
            text("INSERT INTO built_resume_skills (built_resume_id, skill_id, shown, position) VALUES (:r, :s, true, 99)"),
            {"r": uuid.UUID(first), "s": skill},
        )
        await session.commit()

    # The first resume now prints Kubernetes, so a new one is no duplicate of it
    second = await _generate(client, me)
    choices = (await client.get(f"{me}/built-resumes/{second}/choices")).json()
    names = {s["skill_id"] for s in choices["skills"]}
    bank_skills = {s["id"]: s["name"] for s in (await client.get(f"{me}/bank")).json()["skills"]}
    assert "Kubernetes" not in {bank_skills.get(i) for i in names}
    assert all(i in bank_skills for i in names)


async def test_generate_matches_a_resume_only_on_what_it_prints(student):
    # A bank fix shows on every resume, so it changes nothing between them.
    client, me = student
    await _fill_bank(client, me)
    first = await _generate(client, me)
    tutor = next(e for e in (await client.get(f"{me}/bank")).json()["entries"] if e["title"] == "Tutor")
    await client.patch(f"{me}/bank/bullets/{tutor['bullets'][0]['id']}", json={"text": "Tutored 45 students"})
    res = await client.post(f"{me}/built-resumes", json={})
    assert (res.status_code, res.json()["detail"]["built_resume_id"]) == (409, first)


async def test_generate_is_no_duplicate_of_a_resume_set_on_another_page(student):
    client, me = student
    await _fill_bank(client, me)
    first = await _generate(client, me)
    settings = {"font_size": 12, "line_spacing": 1.15, "side_margin": 0.75, "top_margin": 0.75, "alignment": "justified", "section_spacing": 4, "entry_spacing": 2, "accent": "#14532D", "bullet": "dash", "show_divider": False, "header_alignment": "left"}
    assert (await client.put(f"{me}/built-resumes/{first}/page-settings", json=settings)).status_code == 204
    assert (await client.post(f"{me}/built-resumes", json={})).status_code == 201


class _FakeBucket:
    def upload(self, path, contents, options):
        return {"path": path}

    def remove(self, paths):
        return []


class _FakeSupabase:
    class storage:
        @staticmethod
        def from_(bucket):
            return _FakeBucket()


async def _upload(client, me):
    files = {"file": ("resume.pdf", b"%PDF-1.4 not really a pdf", "application/pdf")}
    return await client.post(f"{me}/resumes", files=files)


async def test_five_uploads_and_no_sixth_however_many_are_generated(student, monkeypatch):
    monkeypatch.setattr("app.routers.resumes.get_supabase", lambda: _FakeSupabase())
    monkeypatch.setattr("app.routers.resumes._extract", _no_text)
    client, me = student
    # Generated resumes count for nothing (KAN-268): six of them leave room
    # for five uploads.
    for _ in range(6):
        await _another(client, me)
    uploads = []
    for _ in range(5):
        res = await _upload(client, me)
        assert res.status_code == 200
        uploads.append(res.json()["id"])

    res = await _upload(client, me)
    assert res.status_code == 409
    assert "5 resumes" in res.json()["detail"]
    await _new_skill(client, me)
    assert (await client.post(f"{me}/built-resumes", json={})).status_code == 201

    # Deleting one makes room again.
    assert (await client.delete(f"{me}/resumes/{uploads[0]}")).status_code == 200
    assert (await _upload(client, me)).status_code == 200


async def _no_text(contents, ext):
    return ""


async def test_a_tailored_resume_names_its_posting_and_says_when_it_has_closed(student, database):
    client, me = student
    applicant_id = uuid.UUID(me.split("/")[2])
    base = await _generate(client, me)
    async with database() as session:
        posting = await session.scalar(
            text(
                "INSERT INTO job_postings (id, title, status, company_name, apply_url) VALUES"
                " (gen_random_uuid(), 'Intern', 'published', 'Acme', 'https://example.com/apply') RETURNING id"
            )
        )
        await session.execute(
            text("UPDATE job_postings SET company_logo_url = 'https://example.com/acme.png',"
                 " company_domain = 'acme.com' WHERE id = :p"),
            {"p": posting},
        )
        tailored = await session.scalar(
            text(
                "INSERT INTO built_resumes (applicant_id, name, template, job_posting_id)"
                " VALUES (:a, 'Acme – Intern', 'jakes', :p) RETURNING id"
            ),
            {"a": applicant_id, "p": posting},
        )
        await session.commit()

    async def postings() -> dict[str, tuple]:
        rows = (await client.get(f"{me}/built-resumes")).json()
        return {r["id"]: (r["posting_title"], r["posting_company"], r["posting_closed"]) for r in rows}

    # The card names the posting and links to it (KAN-268).
    assert await postings() == {base: (None, None, False), str(tailored): ("Intern", "Acme", False)}
    # ...and shows its company's logo (2026-11-10)
    rows = {r["id"]: r for r in (await client.get(f"{me}/built-resumes")).json()}
    assert (rows[str(tailored)]["posting_logo_url"], rows[str(tailored)]["posting_company_domain"]) == (
        "https://example.com/acme.png", "acme.com")
    assert rows[base]["posting_logo_url"] is None
    async with database() as session:
        await session.execute(text("UPDATE job_postings SET status = 'closed' WHERE id = :p"), {"p": posting})
        await session.commit()
    assert await postings() == {base: (None, None, False), str(tailored): ("Intern", "Acme", True)}


async def test_the_default_resume_is_an_uploaded_or_a_base_resume(student, monkeypatch):
    monkeypatch.setattr("app.routers.resumes.get_supabase", lambda: _FakeSupabase())
    monkeypatch.setattr("app.routers.resumes._extract", _no_text)
    client, me = student
    upload = (await _upload(client, me)).json()
    uploaded = upload["id"]
    assert upload["is_default"] is True  # the student's only resume
    built = await _generate(client, me)
    # A second resume leaves the default where it was.
    assert [r["is_default"] for r in (await client.get(f"{me}/built-resumes")).json()] == [False]

    assert (await client.put(f"{me}/resumes/{uploaded}/default")).status_code == 200
    assert (await client.put(f"{me}/built-resumes/{built}/default")).status_code == 200
    assert [r["is_default"] for r in (await client.get(f"{me}/built-resumes")).json()] == [True]
    assert [r["is_default"] for r in (await client.get(f"{me}/resumes")).json()] == [False]

    assert (await client.put(f"{me}/resumes/{uploaded}/default")).status_code == 200
    assert [r["is_default"] for r in (await client.get(f"{me}/built-resumes")).json()] == [False]
    assert [r["is_default"] for r in (await client.get(f"{me}/resumes")).json()] == [True]

    # Deleting the default base resume makes the one left the default.
    await client.put(f"{me}/built-resumes/{built}/default")
    await client.delete(f"{me}/built-resumes/{built}")
    assert [r["is_default"] for r in (await client.get(f"{me}/resumes")).json()] == [True]

    # And deleting an uploaded resume makes the base resume left the default.
    built = await _generate(client, me)
    await client.delete(f"{me}/resumes/{uploaded}")
    assert [r["is_default"] for r in (await client.get(f"{me}/built-resumes")).json()] == [True]


async def test_a_tailored_resume_can_be_the_default(student, database):
    """KAN-268: the API refused a tailored resume's star until then."""
    client, me = student
    base = await _generate(client, me)
    async with database() as session:
        posting = await session.scalar(
            text(
                "INSERT INTO job_postings (id, title, status, company_name, apply_url) VALUES"
                " (gen_random_uuid(), 'Intern', 'published', 'Acme', 'https://example.com/apply') RETURNING id"
            )
        )
        tailored = await session.scalar(
            text(
                "INSERT INTO built_resumes (applicant_id, name, template, job_posting_id)"
                " VALUES (:a, 'Tailored', 'jakes', :p) RETURNING id"
            ),
            {"a": uuid.UUID(me.split("/")[2]), "p": posting},
        )
        await session.commit()

    assert (await client.put(f"{me}/built-resumes/{tailored}/default")).status_code == 200
    stars = {r["id"]: r["is_default"] for r in (await client.get(f"{me}/built-resumes")).json()}
    assert stars == {str(tailored): True, base: False}
    assert (await client.put(f"{me}/built-resumes/{uuid.uuid4()}/default")).status_code == 404


async def _tailored(database, me) -> str:
    async with database() as session:
        posting = await session.scalar(
            text(
                "INSERT INTO job_postings (id, title, status, company_name, apply_url) VALUES"
                " (gen_random_uuid(), 'Intern', 'published', 'Acme', :url) RETURNING id"
            ),
            {"url": f"https://example.com/{uuid.uuid4()}"},
        )
        tailored = await session.scalar(
            text(
                "INSERT INTO built_resumes (applicant_id, name, template, job_posting_id)"
                " VALUES (:a, 'Tailored', 'jakes', :p) RETURNING id"
            ),
            {"a": uuid.UUID(me.split("/")[2]), "p": posting},
        )
        await session.commit()
    return str(tailored)


async def test_a_tailored_resume_left_alone_becomes_the_default(student, database):
    """A tailored resume can be the default since KAN-268, but the one-resume
    rule still counted base resumes only: deleting the base left the
    tailored resume with no star."""
    client, me = student
    base = await _generate(client, me)
    tailored = await _tailored(database, me)

    assert (await client.delete(f"{me}/built-resumes/{base}")).status_code == 204
    assert [(r["id"], r["is_default"]) for r in (await client.get(f"{me}/built-resumes")).json()] == [
        (tailored, True)]


async def test_a_starred_tailored_resume_keeps_its_star_beside_one_upload(student, database, monkeypatch):
    # The same rule saw an upload and a tailored resume as one resume, so
    # every add or delete moved the star to the upload.
    monkeypatch.setattr("app.routers.resumes.get_supabase", lambda: _FakeSupabase())
    monkeypatch.setattr("app.routers.resumes._extract", _no_text)
    client, me = student
    upload = (await _upload(client, me)).json()["id"]
    tailored = await _tailored(database, me)
    assert (await client.put(f"{me}/built-resumes/{tailored}/default")).status_code == 200

    base = await _another(client, me)  # the seeded tailored resume is empty
    assert (await client.delete(f"{me}/built-resumes/{base}")).status_code == 204
    assert [r["is_default"] for r in (await client.get(f"{me}/built-resumes")).json()] == [True]
    assert [(r["id"], r["is_default"]) for r in (await client.get(f"{me}/resumes")).json()] == [(upload, False)]


async def test_an_entry_says_how_many_built_resumes_show_it(student, database):
    """Story 18: the delete confirm names the resumes an entry is on."""
    client, me = student
    await _fill_bank(client, me)
    entry = next(e for e in (await client.get(f"{me}/bank")).json()["entries"] if e["title"] == "Tutor")
    url = f"{me}/bank/entries/{entry['id']}/resumes"
    assert (await client.get(url)).json() == {"built_resumes": 0}

    first = await _generate(client, me)
    await _another(client, me)
    assert (await client.get(url)).json() == {"built_resumes": 2}

    hide = {"entries": [{"entry_id": entry["id"], "shown": False}]}
    assert (await client.patch(f"{me}/built-resumes/{first}/choices", json=hide)).status_code == 200
    assert (await client.get(url)).json() == {"built_resumes": 1}

    async with database() as session:
        other = await _seed_applicant(session)
    assert (await client.get(f"/applicants/{other}/bank/entries/{entry['id']}/resumes")).status_code == 403
    assert (await client.get(f"{me}/bank/entries/{uuid.uuid4()}/resumes")).status_code == 404


async def test_another_students_built_resumes_are_out_of_reach(student, database):
    client, me = student
    async with database() as session:
        other = await _seed_applicant(session)
    _sign_in(other)
    theirs = await _generate(client, f"/applicants/{other}")
    _sign_in(uuid.UUID(me.split("/")[2]))

    assert (await client.get(f"/applicants/{other}/built-resumes")).status_code == 403
    assert (await client.post(f"/applicants/{other}/built-resumes", json={})).status_code == 403
    for path in ("docx", "render"):
        assert (await client.get(f"{me}/built-resumes/{theirs}/{path}")).status_code == 404
    assert (await client.put(f"{me}/built-resumes/{theirs}/default")).status_code == 404
    assert (await client.delete(f"{me}/built-resumes/{theirs}")).status_code == 404


def _tectonic_or_skip() -> None:
    from tests.test_resume_render import _tectonic_or_skip as check

    check()


def _pdf_text(encoded: str) -> str:
    import base64
    import io

    from pdfminer.high_level import extract_text

    return " ".join(extract_text(io.BytesIO(base64.b64decode(encoded))).split())


async def test_generate_then_render_gives_a_one_page_pdf_with_the_bank(student):
    _tectonic_or_skip()
    client, me = student
    await _fill_bank(client, me)
    resume_id = await _generate(client, me, "Data/ML: 2027")

    res = await client.get(f"{me}/built-resumes/{resume_id}/render")
    assert res.status_code == 200
    body = res.json()
    # The editor's Download PDF saves it under this (KAN-267), header-safe.
    assert body["file_name"] == "DataML 2027.pdf"
    assert body["page_count"] == 1
    assert body["missing_characters"] == []
    text = _pdf_text(body["pdf"])
    for expected in ("Sam Seeker", "Stony Brook University", "Software Intern", "Cut page load time by 30%",
                     # TeX's font mapping prints a straight apostrophe curly
                     "Dean’s List | Stony Brook University", "Languages: Python"):
        assert expected in text


async def test_render_gives_the_editor_a_box_for_each_line_with_bank_ids(student):
    _tectonic_or_skip()
    client, me = student
    await _fill_bank(client, me)
    resume_id = await _generate(client, me)
    bank = (await client.get(f"{me}/bank")).json()

    boxes = (await client.get(f"{me}/built-resumes/{resume_id}/render")).json()["boxes"]
    assert boxes and all(set(b) == {"item_id", "kind", "page", "x0", "y0", "x1", "y1", "text"} for b in boxes)
    by_item = {}
    for b in boxes:
        by_item.setdefault(b["item_id"], set()).add(b["kind"])
    intern = next(e for e in bank["entries"] if e["title"] == "Software Intern")
    assert by_item[intern["id"]] == {"title", "organization", "location", "dates"}
    for bullet in intern["bullets"]:
        assert by_item[bullet["id"]] == {"bullet"}
    school = next(e for e in bank["entries"] if e["section"] == "education")
    assert by_item[school["id"]] == {"title", "location", "degree", "dates", "gpa", "coursework"}
    for skill in bank["skills"]:
        assert by_item[skill["id"]] == {"skill"}
    # PDF points from the top left of a Letter page
    assert all(b["page"] == 1 and 0 <= b["x0"] < b["x1"] <= 612 and 0 <= b["y0"] < b["y1"] <= 792 for b in boxes)


async def test_render_reports_a_long_resume_and_the_characters_the_font_lacks(student):
    _tectonic_or_skip()
    client, me = student
    bullets = [f"Organized event number {i} for two hundred members of the society" for i in range(30)]
    for title in ("Президент", "Treasurer"):
        res = await client.post(f"{me}/bank/entries", json={"section": "leadership", "title": title,
                                                            "organization": "Chess Society", "bullets": bullets})
        assert res.status_code == 201
    resume_id = await _generate(client, me)

    body = (await client.get(f"{me}/built-resumes/{resume_id}/render")).json()
    assert body["page_count"] == 2
    assert body["missing_characters"] == ["П", "р", "е", "з", "и", "д", "н", "т"]


async def test_render_answers_503_when_tectonic_is_missing(student, monkeypatch):
    from app.services.resume_render import TectonicUnavailable

    def missing(view, identity, template, page):
        raise TectonicUnavailable("no tectonic binary")

    monkeypatch.setattr("app.routers.built_resumes.render", missing)
    client, me = student
    resume_id = await _generate(client, me)

    res = await client.get(f"{me}/built-resumes/{resume_id}/render")
    assert res.status_code == 503
    assert res.json() == {"detail": "The PDF could not be made. Try again, or download the Word file."}


async def test_recommendations_work_when_the_default_is_a_base_resume(student, monkeypatch):
    async def no_embedding(texts, *, timeout=None, query=False):
        return None

    monkeypatch.setattr("app.queries.jobs.recommendations.embed", no_embedding)
    client, me = student
    applicant_id = uuid.UUID(me.split("/")[2])
    await _fill_bank(client, me)
    built = await _generate(client, me)
    await client.put(f"{me}/built-resumes/{built}/default")

    # The recommender reads the bank (KAN-212), whichever resume is the default.
    assert (await client.get(f"/jobs/recommended/{applicant_id}")).status_code == 200


def _at(value: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(value)


async def test_a_resume_made_with_no_name_is_numbered_past_the_highest_in_use(student):
    """KAN-258: every resume made with no name was "Base Resume"."""
    client, me = student
    first = (await client.post(f"{me}/built-resumes", json={})).json()
    await _new_skill(client, me)
    second = (await client.post(f"{me}/built-resumes", json={})).json()
    assert (first["name"], second["name"]) == ("Resume #1", "Resume #2")

    # A deleted number is not handed out again while a higher one is left.
    assert (await client.delete(f"{me}/built-resumes/{first['id']}")).status_code == 204
    await _new_skill(client, me)
    assert (await client.post(f"{me}/built-resumes", json={})).json()["name"] == "Resume #3"


async def test_rename_changes_the_name_and_frees_its_number(student):
    client, me = student
    resume_id = (await client.post(f"{me}/built-resumes", json={})).json()["id"]

    res = await client.patch(f"{me}/built-resumes/{resume_id}", json={"name": "  Data Science  "})
    assert res.status_code == 200
    renamed = res.json()
    assert renamed["name"] == "Data Science"
    assert _at(renamed["edited_at"]) > _at(renamed["created_at"])
    assert [r["name"] for r in (await client.get(f"{me}/built-resumes")).json()] == ["Data Science"]

    assert (await client.patch(f"{me}/built-resumes/{resume_id}", json={"name": "   "})).status_code == 422
    assert (await client.patch(f"{me}/built-resumes/{uuid.uuid4()}", json={"name": "X"})).status_code == 404
    # No resume holds "Resume #1" any more, so the next one takes it.
    await _new_skill(client, me)
    assert (await client.post(f"{me}/built-resumes", json={})).json()["name"] == "Resume #1"


async def test_edited_at_is_created_at_until_the_resume_itself_changes(student):
    client, me = student
    await _fill_bank(client, me)
    resume_id = await _generate(client, me)
    made = (await client.get(f"{me}/built-resumes")).json()[0]
    assert _at(made["edited_at"]) == _at(made["created_at"])

    bank = (await client.get(f"{me}/bank")).json()
    bullet = next(e for e in bank["entries"] if e["title"] == "Software Intern")["bullets"][0]["id"]
    res = await client.patch(f"{me}/built-resumes/{resume_id}/choices",
                             json={"bullets": [{"bullet_id": bullet, "shown": False}]})
    assert res.status_code == 200

    edited = (await client.get(f"{me}/built-resumes")).json()[0]
    assert _at(edited["edited_at"]) > _at(edited["created_at"])


# Start From a Resume You Have (2026-11-11): the Resumes page's Generate
# Resume dialog copies a built resume or starts one from an upload.


async def _copy(client, me, **source) -> httpx.Response:
    return await client.post(f"{me}/built-resumes/copy", json={k: str(v) for k, v in source.items()})


async def test_a_copy_prints_as_its_source_and_owns_its_own_skill_and_wording(student, database):
    client, me = student
    await _fill_bank(client, me)
    source = uuid.UUID(await _generate(client, me, "General SWE"))
    applicant_id = uuid.UUID(me.rsplit("/", 1)[1])
    bank = (await client.get(f"{me}/bank")).json()
    intern = next(e for e in bank["entries"] if e["title"] == "Software Intern")
    tutor = next(e for e in bank["entries"] if e["title"] == "Tutor")
    bullet = uuid.UUID(intern["bullets"][0]["id"])
    async with database() as session:
        # What only the source owns: a Tailor skill and a typed wording.
        skill = await session.scalar(
            text("INSERT INTO bank_skills (applicant_id, name, built_resume_id) VALUES (:a, 'Kubernetes', :r) RETURNING id"),
            {"a": applicant_id, "r": source},
        )
        await session.execute(
            text("INSERT INTO built_resume_skills (built_resume_id, skill_id, shown, position) VALUES (:r, :s, true, 99)"),
            {"r": source, "s": skill},
        )
        variant = await session.scalar(
            text("INSERT INTO bank_bullet_variants (bullet_id, text, built_resume_id) VALUES (:b, 'Made pages load 30% faster', :r) RETURNING id"),
            {"b": bullet, "r": source},
        )
        await session.execute(
            text("UPDATE built_resume_bullets SET variant_id = :v WHERE built_resume_id = :r AND bullet_id = :b"),
            {"v": variant, "r": source, "b": bullet},
        )
        # And a choice: one entry taken off.
        await session.execute(
            text("UPDATE built_resume_entries SET shown = false WHERE built_resume_id = :r AND entry_id = :e"),
            {"r": source, "e": uuid.UUID(tutor["id"])},
        )
        await session.commit()
    printed = _docx_lines((await client.get(f"{me}/built-resumes/{source}/docx")).content)
    assert any("Made pages load 30% faster" in line for line in printed)
    assert not any("Tutor" in line for line in printed)

    res = await _copy(client, me, built_resume_id=source)
    assert res.status_code == 201, res.text
    copy = res.json()
    assert (copy["name"], copy["job_posting_id"], copy["is_default"]) == ("General SWE (Copy)", None, False)
    assert _docx_lines((await client.get(f"{me}/built-resumes/{copy['id']}/docx")).content) == printed

    async with database() as session:
        owned = (await session.execute(
            text("SELECT (SELECT count(*) FROM bank_skills WHERE built_resume_id = :c),"
                 " (SELECT count(*) FROM bank_bullet_variants WHERE built_resume_id = :c)"),
            {"c": uuid.UUID(copy["id"])},
        )).one()
    assert tuple(owned) == (1, 1)  # its own rows, not the source's

    # The source goes; the copy prints as it did.
    assert (await client.delete(f"{me}/built-resumes/{source}")).status_code == 204
    assert _docx_lines((await client.get(f"{me}/built-resumes/{copy['id']}/docx")).content) == printed


async def test_a_copy_of_a_tailored_resume_leaves_its_posting_and_is_numbered(student, database):
    client, me = student
    tailored = await _tailored(database, me)
    first = (await _copy(client, me, built_resume_id=tailored)).json()
    second = (await _copy(client, me, built_resume_id=tailored)).json()
    assert (first["name"], first["job_posting_id"]) == ("Tailored (Copy)", None)
    assert second["name"] == "Tailored (Copy 2)"


async def test_starting_from_an_upload_shows_only_that_uploads_entries(student, monkeypatch):
    monkeypatch.setattr("app.routers.resumes.get_supabase", lambda: _FakeSupabase())
    monkeypatch.setattr("app.routers.resumes._extract", _no_text)
    client, me = student
    uploads = []
    for title in ("Data Intern", "Barista"):
        upload = (await _upload(client, me)).json()["id"]
        uploads.append(upload)
        res = await client.post(
            f"{me}/bank/entries?resume_id={upload}",
            json={"section": "experience", "title": title, "organization": "Acme", "start_month": "2025-06",
                  "end_month": "2025-08", "bullets": [f"Did {title} work"]},
        )
        assert res.status_code == 201, res.text

    res = await _copy(client, me, uploaded_resume_id=uploads[0])
    assert res.status_code == 201, res.text
    made = res.json()
    assert made["name"] == "resume (Copy)"  # the file's name, resume.pdf
    lines = _docx_lines((await client.get(f"{me}/built-resumes/{made['id']}/docx")).content)
    assert any("Data Intern" in line for line in lines)
    assert not any("Barista" in line for line in lines)


async def test_starting_from_an_empty_upload_is_refused(student, monkeypatch):
    monkeypatch.setattr("app.routers.resumes.get_supabase", lambda: _FakeSupabase())
    monkeypatch.setattr("app.routers.resumes._extract", _no_text)
    client, me = student
    upload = (await _upload(client, me)).json()["id"]
    res = await _copy(client, me, uploaded_resume_id=upload)
    assert res.status_code == 409
    assert (await client.get(f"{me}/built-resumes")).json() == []


async def test_starting_from_a_resume_needs_one_source_of_the_students_own(student):
    client, me = student
    mine = await _generate(client, me)
    assert (await client.post(f"{me}/built-resumes/copy", json={})).status_code == 422
    both = {"built_resume_id": mine, "uploaded_resume_id": str(uuid.uuid4())}
    assert (await client.post(f"{me}/built-resumes/copy", json=both)).status_code == 422
    assert (await _copy(client, me, built_resume_id=uuid.uuid4())).status_code == 404
    assert (await _copy(client, me, uploaded_resume_id=uuid.uuid4())).status_code == 404
