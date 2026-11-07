"""
Seam-1 tests for import (KAN-211, ADR 0003, ADR 0005) on real Postgres: an
upload, Import Updated Resume and Import Again read a resume and write it into
the experience bank as that upload's own entries and skills, replacing what
it owned and never merging into another resume's. Every reading asks the
model first while the student has an AI reading left, the parser behind it
(KAN-732, ADR 0007); conftest's `_model_down` makes the model unreachable in
every test that installs none, so those read with the parser.
backend/CLAUDE.md's Tests section has the setup.
"""

import json
import uuid

import httpx
import pytest
from openai import RateLimitError
from sqlalchemy import text
from workit_scout.testing import ScriptedLLM

from app.config import get_settings
from app.deps import get_current_account
from app.main import app
from app.routers import resumes as resumes_router
from app.routers.resumes import text_hash
from app.schemas.auth import AccountType, AuthenticatedAccount
from app.services.bank_import import read, skill_pairs
from tests import fake_models

pytestmark = pytest.mark.anyio

# Starts at the first section header, like the parser fixtures: no contact details.
RESUME_TEXT = """\
Education
Riverside State University  Expected May 2099
B.S. in Mechanical Engineering
•GPA: 3.62
•Coursework: Thermodynamics, Fluid Mechanics, Statics
Experience
Harbor Robotics  Jun 2026 - Aug 2026
Mechanical Engineering Intern  Portland, OR
•Designed a sheet-metal bracket that cut assembly time by 20%
•Ran tolerance stack-up analyses in SolidWorks
Projects
Budget Buddy  Jan 2026 - Mar 2026
https://github.com/example/budget-buddy
•Built a shared expense tracker
Leadership & Activities
Society of Women Engineers  Sep 2025 - Present
Vice President  Riverside, CA
•Organized 12 technical workshops
Awards
Dean's List – Riverside State University  Dec 2025
Certifications
Certified SolidWorks Associate – Dassault Systemes
Skills
•Tools: SolidWorks, MATLAB
"""


async def _seed_applicant(session) -> uuid.UUID:
    applicant_id = uuid.uuid4()
    await session.execute(text("INSERT INTO auth.users (id) VALUES (:id)"), {"id": applicant_id})
    await session.execute(
        text("INSERT INTO applicant_profiles (id, email, full_name) VALUES (:id, :email, 'Sam Seeker')"),
        {"id": applicant_id, "email": f"{applicant_id.hex[:8]}@example.com"},
    )
    await session.commit()
    return applicant_id


async def _seed_resume(
    database, applicant_id: uuid.UUID, raw_text: str | None, *, minutes_ago: int = 0, digest: str | None = None
) -> uuid.UUID:
    resume_id = uuid.uuid4()
    async with database() as session:
        await session.execute(
            text(
                "INSERT INTO resumes (id, applicant_id, original_filename, storage_path, status, raw_text,"
                " text_hash, created_at)"
                " VALUES (:id, :applicant, 'resume.pdf', :path, 'parsed', :raw, :digest,"
                " now() - make_interval(mins => :ago))"
            ),
            {"id": resume_id, "applicant": applicant_id, "path": f"{applicant_id}/{resume_id}.pdf", "raw": raw_text,
             "digest": digest, "ago": minutes_ago},
        )
        await session.commit()
    return resume_id


async def _set_default(database, applicant_id: uuid.UUID, resume_id: uuid.UUID) -> None:
    async with database() as session:
        await session.execute(
            text("UPDATE applicant_profiles SET default_resume_id = :r WHERE id = :a"),
            {"r": resume_id, "a": applicant_id},
        )
        await session.commit()


def _sign_in(applicant_id: uuid.UUID) -> None:
    app.dependency_overrides[get_current_account] = lambda: AuthenticatedAccount(
        id=applicant_id,
        email="sam@example.com",
        full_name="Sam Seeker",
        account_type=AccountType.APPLICANT,
        onboarding_completed=True,
    )


@pytest.fixture
async def student(database):
    """A signed-in applicant and an API client. Yields (client, applicant id, bank URL)."""
    async with database() as session:
        applicant_id = await _seed_applicant(session)
    _sign_in(applicant_id)
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, applicant_id, f"/applicants/{applicant_id}/bank"
    finally:
        app.dependency_overrides.pop(get_current_account, None)



def _summary(entry: dict) -> tuple:
    return (entry["section"], entry["title"], entry["organization"])


def _counts(body: dict) -> tuple:
    return (body["entries_added"], body["skills_added"])


class _Bucket:
    """The Resume bucket, in memory."""

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.removed: list[str] = []
        self.storage = self

    def from_(self, bucket):
        return self

    def upload(self, path, contents, options):
        self.files[path] = contents

    def remove(self, paths):
        self.removed.extend(paths)


@pytest.fixture
def upload(monkeypatch):
    """Uploads a file whose extracted text is the given string. Returns the
    in-memory bucket beside the call."""
    bucket = _Bucket()
    monkeypatch.setattr("app.routers.resumes.get_supabase", lambda: bucket)

    async def send(client, applicant_id, raw_text, *, replacing=None, filename="resume.pdf", preview=False,
                   replace_matching=False, removed_skills=(), reading=None):
        """With `replacing`, Import Updated Resume on that resume's row; with
        `preview`, the parse preview, which saves nothing; with
        `replace_matching`, the upload that confirms a preview (KAN-372),
        and with `reading` the preview's reading it saves (KAN-732)."""
        async def extract(contents, ext):
            return raw_text

        monkeypatch.setattr("app.routers.resumes._extract", extract)
        files = {"file": (filename, b"%PDF-1.4 not really a pdf", "application/pdf")}
        if replacing:
            return await client.put(f"/applicants/{applicant_id}/resumes/{replacing}", files=files)
        if preview:
            return await client.post(f"/applicants/{applicant_id}/resumes/preview", files=files)
        params = {"replace": "matching"} if replace_matching else None
        data = {"removed_skills": list(removed_skills)} if removed_skills else {}
        if reading is not None:
            data["reading"] = reading
        return await client.post(f"/applicants/{applicant_id}/resumes", files=files, params=params, data=data or None)

    send.bucket = bucket
    return send


# --- upload fills the bank ------------------------------------------------------


async def test_an_upload_writes_its_reading_into_the_bank(student, upload):
    client, applicant_id, bank = student

    res = await upload(client, applicant_id, RESUME_TEXT)
    assert res.status_code == 200
    body = res.json()
    assert "parsed_json" not in body
    assert body["status"] == "parsed"
    assert body["bank"] == {
        "found": 8, "entries_added": 6, "skills_added": 2, "entries_replaced": 0, "skills_replaced": 0,
        "read_by": "parser", "uses_left": 1,
    }

    saved = (await client.get(bank)).json()
    # The bank's own order: section order, ongoing first, then newest.
    assert [_summary(e) for e in saved["entries"]] == [
        ("education", "Riverside State University", None),
        ("experience", "Mechanical Engineering Intern", "Harbor Robotics"),
        ("projects", "Budget Buddy", None),
        ("leadership", "Vice President", "Society of Women Engineers"),
        ("awards", "Dean's List", "Riverside State University"),
        ("certifications", "Certified SolidWorks Associate", None),
    ]
    education, job, project, club, award, cert = saved["entries"]

    assert (education["degree"], education["field_of_study"], education["gpa"]) == ("B.S", "Mechanical Engineering", 3.62)
    assert education["coursework"] == ["Thermodynamics", "Fluid Mechanics", "Statics"]
    assert (education["end_month"], education["end_kind"]) == ("2099-05", "expected")
    assert education["bullets"] == []

    # The resume's own words, unchanged.
    assert [b["text"] for b in job["bullets"]] == [
        "Designed a sheet-metal bracket that cut assembly time by 20%",
        "Ran tolerance stack-up analyses in SolidWorks",
    ]
    assert (job["location"], job["start_month"], job["end_month"], job["end_kind"]) == (
        "Portland, OR", "2026-06", "2026-08", "month",
    )
    assert project["link"] == "https://github.com/example/budget-buddy"
    assert [b["text"] for b in project["bullets"]] == ["Built a shared expense tracker"]
    assert (club["start_month"], club["end_month"], club["end_kind"]) == ("2025-09", None, "present")
    assert (award["award_date"], award["start_month"], award["end_kind"]) == ("2025-12", None, None)
    assert cert["issuer"] == "Dassault Systemes"
    assert [(s["name"], s["group"]) for s in saved["skills"]] == [("MATLAB", "Tools"), ("SolidWorks", "Tools")]


async def test_an_upload_never_merges_into_an_entry_the_bank_has(student, upload):
    client, applicant_id, bank = student
    # What the student typed before uploading: the same job and skill.
    mine = (
        await client.post(
            f"{bank}/entries",
            json={"section": "experience", "title": "mechanical engineering intern", "organization": "HARBOR ROBOTICS"},
        )
    ).json()
    await client.post(f"{bank}/skills", json={"name": "matlab"})

    body = (await upload(client, applicant_id, RESUME_TEXT)).json()["bank"]
    assert _counts(body) == (6, 2)

    saved = (await client.get(bank)).json()
    jobs = [e for e in saved["entries"] if e["section"] == "experience"]
    # Two rows: the student's, untouched, and the upload's own.
    assert len(jobs) == 2
    kept = next(j for j in jobs if j["id"] == mine["id"])
    assert (kept["title"], kept["start_month"], kept["bullets"]) == ("mechanical engineering intern", None, [])
    assert sorted(s["name"] for s in saved["skills"]) == ["MATLAB", "SolidWorks", "matlab"]


# --- duplicates (KAN-267) ---------------------------------------------------------


def test_the_text_hash_ignores_layout_and_ligatures_but_not_words_or_case():
    assert text_hash("Built a  ﬁle tracker\n\n•Python ") == text_hash("Built a file tracker •Python")
    assert text_hash("Built a file tracker") != text_hash("Built a file tracker.")
    assert text_hash("Built a file tracker") != text_hash("built a file tracker")
    assert text_hash("") is None and text_hash(" \n ") is None and text_hash(None) is None


async def test_the_same_resume_twice_is_refused_and_keeps_nothing(student, upload):
    client, applicant_id, bank = student
    first = (await upload(client, applicant_id, RESUME_TEXT, filename="Sam 2026.pdf")).json()

    res = await upload(client, applicant_id, RESUME_TEXT, filename="Sam 2026 (1).pdf")
    assert res.status_code == 409
    assert res.json()["detail"] == {"message": "Duplicate Resume found: Sam 2026.pdf", "resume_id": first["id"]}
    assert list(upload.bucket.files) == [first["storage_path"]]
    assert [r["id"] for r in (await client.get(f"/applicants/{applicant_id}/resumes")).json()] == [first["id"]]
    assert len((await client.get(bank)).json()["entries"]) == 6


async def test_the_same_words_exported_again_are_a_duplicate_and_one_new_word_is_not(student, upload):
    client, applicant_id, _ = student
    await upload(client, applicant_id, RESUME_TEXT)

    reflowed = RESUME_TEXT.replace("\n", "\n\n").replace("  ", "    ")
    assert (await upload(client, applicant_id, reflowed)).status_code == 409
    assert (await upload(client, applicant_id, UPDATED_TEXT)).status_code == 200


async def test_uploads_with_no_text_are_never_duplicates(student, upload):
    client, applicant_id, _ = student
    assert (await upload(client, applicant_id, "")).status_code == 200
    assert (await upload(client, applicant_id, "")).status_code == 200


async def test_another_students_copy_of_the_resume_uploads(student, upload, database):
    client, applicant_id, _ = student
    async with database() as session:
        other = await _seed_applicant(session)
    await _seed_resume(database, other, RESUME_TEXT, digest=text_hash(RESUME_TEXT))
    assert (await upload(client, applicant_id, RESUME_TEXT)).status_code == 200


async def test_two_uploads_at_once_keep_one(student, upload, monkeypatch):
    client, applicant_id, _ = student
    first = (await upload(client, applicant_id, RESUME_TEXT)).json()

    # The second request checked before the first was saved: the unique
    # index refuses it at the commit, and it removes its file.
    real = resumes_router._duplicate_of
    checks = []

    async def checked_too_early(*args, **kwargs):
        checks.append(args)
        return None if len(checks) == 1 else await real(*args, **kwargs)

    monkeypatch.setattr("app.routers.resumes._duplicate_of", checked_too_early)
    res = await upload(client, applicant_id, RESUME_TEXT)
    assert res.status_code == 409
    assert res.json()["detail"]["resume_id"] == first["id"]
    assert upload.bucket.removed == [p for p in upload.bucket.files if p != first["storage_path"]]
    assert len((await client.get(f"/applicants/{applicant_id}/resumes")).json()) == 1


async def test_an_upload_the_parser_cannot_read_adds_nothing(student, upload):
    client, applicant_id, bank = student

    res = await upload(client, applicant_id, UNREADABLE_TEXT)
    assert res.status_code == 200
    assert res.json()["status"] == "parse_failed"
    assert (res.json()["bank"]["found"], _counts(res.json()["bank"])) == (0, (0, 0))
    saved = (await client.get(bank)).json()
    assert (saved["entries"], saved["skills"]) == ([], [])


async def test_a_failed_bank_write_keeps_no_resume_and_no_file(student, upload, monkeypatch):
    client, applicant_id, _ = student

    async def broken(*args, **kwargs):
        raise RuntimeError("the database went away")

    monkeypatch.setattr("app.services.bank.import_upload", broken)
    res = await upload(client, applicant_id, RESUME_TEXT)
    assert res.status_code == 500
    assert upload.bucket.removed == list(upload.bucket.files)
    assert (await client.get(f"/applicants/{applicant_id}/resumes")).json() == []


# --- Import Updated Resume --------------------------------------------------------

UPDATED_TEXT = RESUME_TEXT.replace(
    "•Ran tolerance stack-up analyses in SolidWorks\n",
    "•Ran tolerance stack-up analyses in SolidWorks\n•Wrote the test plan for the bracket\n",
)


async def test_an_updated_resume_replaces_the_rows_file_and_its_entries(student, upload, database):
    client, applicant_id, bank = student
    first = (await upload(client, applicant_id, RESUME_TEXT)).json()
    await _set_default(database, applicant_id, uuid.UUID(first["id"]))

    res = await upload(client, applicant_id, UPDATED_TEXT, replacing=first["id"], filename="resume-v2.pdf")
    assert res.status_code == 200
    body = res.json()
    assert (body["id"], body["original_filename"], body["is_default"]) == (first["id"], "resume-v2.pdf", True)
    assert body["storage_path"] != first["storage_path"]
    assert (body["bank"]["found"], _counts(body["bank"])) == (8, (6, 2))
    assert upload.bucket.removed == [first["storage_path"]]

    listed = (await client.get(f"/applicants/{applicant_id}/resumes")).json()
    assert [(r["id"], r["storage_path"]) for r in listed] == [(first["id"], body["storage_path"])]
    saved = (await client.get(bank)).json()
    # Replaced, not copied: one set of the upload's entries and skills.
    assert (len(saved["entries"]), len(saved["skills"])) == (6, 2)
    internship = next(e for e in saved["entries"] if e["section"] == "experience")
    assert "Wrote the test plan for the bracket" in [b["text"] for b in internship["bullets"]]


async def _sent_from(database, applicant_id, upload: dict) -> uuid.UUID:
    """A sent resume pointing at the upload's file, as Apply leaves one."""
    async with database() as session:
        sent = await session.scalar(
            text(
                "INSERT INTO sent_resumes (applicant_id, storage_path, name, uploaded_resume_id)"
                " VALUES (:a, :path, 'resume.pdf', :r) RETURNING id"
            ),
            {"a": applicant_id, "path": upload["storage_path"], "r": uuid.UUID(upload["id"])},
        )
        await session.commit()
    return sent


async def test_an_updated_resume_freezes_the_old_files_sent_resumes_and_removes_it(student, upload, database):
    """KAN-267: the old file stayed while a sent resume used it. The sent
    resume becomes a snapshot of the old text, and the file goes."""
    client, applicant_id, _ = student
    first = (await upload(client, applicant_id, RESUME_TEXT)).json()
    sent = await _sent_from(database, applicant_id, first)

    res = await upload(client, applicant_id, UPDATED_TEXT, replacing=first["id"])
    assert res.status_code == 200
    assert upload.bucket.removed == [first["storage_path"]]
    async with database() as session:
        row = (await session.execute(text(
            "SELECT s.storage_path, r.source FROM sent_resumes s JOIN resume_snapshots r ON r.id = s.snapshot_id"
            " WHERE s.id = :id"), {"id": sent})).one()
    assert tuple(row) == (None, "upload")


async def test_an_updated_resume_with_no_text_keeps_the_old_file_a_sent_resume_uses(student, upload, database):
    # Nothing to rebuild the old file from, so it stays while the sent resume uses it.
    client, applicant_id, _ = student
    first = (await upload(client, applicant_id, "")).json()
    await _sent_from(database, applicant_id, first)

    res = await upload(client, applicant_id, UPDATED_TEXT, replacing=first["id"])
    assert res.status_code == 200
    assert upload.bucket.removed == []


async def test_a_failed_update_keeps_the_old_file_and_removes_the_new_one(student, upload, monkeypatch):
    client, applicant_id, _ = student
    first = (await upload(client, applicant_id, RESUME_TEXT)).json()

    async def broken(*args, **kwargs):
        raise RuntimeError("the database went away")

    monkeypatch.setattr("app.services.bank.import_upload", broken)
    res = await upload(client, applicant_id, UPDATED_TEXT, replacing=first["id"])
    assert res.status_code == 500
    new_path = next(p for p in upload.bucket.files if p != first["storage_path"])
    assert upload.bucket.removed == [new_path]
    listed = (await client.get(f"/applicants/{applicant_id}/resumes")).json()
    assert [r["storage_path"] for r in listed] == [first["storage_path"]]


async def test_an_update_may_keep_its_own_text_but_not_take_another_resumes(student, upload):
    client, applicant_id, _ = student
    first = (await upload(client, applicant_id, RESUME_TEXT, filename="one.pdf")).json()
    second = (await upload(client, applicant_id, UPDATED_TEXT, filename="two.pdf")).json()

    # The same words in a new file: how a student swaps the layout.
    assert (await upload(client, applicant_id, RESUME_TEXT, replacing=first["id"])).status_code == 200
    res = await upload(client, applicant_id, RESUME_TEXT, replacing=second["id"])
    assert res.status_code == 409
    assert res.json()["detail"] == {"message": "Duplicate Resume found: resume.pdf", "resume_id": first["id"]}


async def test_another_students_resume_cannot_be_updated(student, upload, database):
    client, applicant_id, _ = student
    async with database() as session:
        other = await _seed_applicant(session)
    theirs = await _seed_resume(database, other, RESUME_TEXT)

    res = await upload(client, applicant_id, UPDATED_TEXT, replacing=theirs)
    assert res.status_code == 404
    assert upload.bucket.files == {}


# --- Import Again ---------------------------------------------------------------


async def test_import_again_writes_into_the_bank_and_replaces_on_a_second_run(student, database):
    client, applicant_id, bank = student
    resume_id = await _seed_resume(database, applicant_id, RESUME_TEXT)

    res = await client.post(f"{bank}/import", json={"resume_id": str(resume_id)})
    assert res.status_code == 200
    body = res.json()
    assert (body["resume_id"], body["filename"], body["read_by"]) == (str(resume_id), "resume.pdf", "parser")
    assert _counts(body) == (6, 2)
    first = {e["id"] for e in (await client.get(bank)).json()["entries"]}

    again = (await client.post(f"{bank}/import", json={"resume_id": str(resume_id)})).json()
    assert _counts(again) == (6, 2)
    saved = (await client.get(bank)).json()
    assert (len(saved["entries"]), len(saved["skills"])) == (6, 2)
    # New rows: the second reading replaced the first.
    assert first.isdisjoint(e["id"] for e in saved["entries"])


async def test_without_a_resume_id_import_reads_the_default_resume_else_the_newest(student, database):
    client, applicant_id, bank = student
    older = await _seed_resume(database, applicant_id, RESUME_TEXT, minutes_ago=10)
    newest = await _seed_resume(database, applicant_id, "Projects\nWorkIt  Jan 2026 - Present\n• Built it")

    res = await client.post(f"{bank}/import", json={})
    assert res.json()["resume_id"] == str(newest)
    assert [e["title"] for e in (await client.get(bank)).json()["entries"]] == ["WorkIt"]

    await _set_default(database, applicant_id, older)
    assert (await client.post(f"{bank}/import", json={})).json()["resume_id"] == str(older)


async def test_a_resume_with_no_readable_sections_writes_nothing(student, database):
    client, applicant_id, bank = student
    unreadable = await _seed_resume(database, applicant_id, None)
    res = await client.post(f"{bank}/import", json={"resume_id": str(unreadable)})
    assert res.status_code == 200
    assert _counts(res.json()) == (0, 0)


async def test_import_with_no_uploaded_resume_is_not_found(student):
    client, _, bank = student
    assert (await client.post(f"{bank}/import", json={})).status_code == 404


async def test_another_students_resume_cannot_be_imported(student, database):
    client, _, bank = student
    async with database() as session:
        other = await _seed_applicant(session)
    theirs = await _seed_resume(database, other, RESUME_TEXT)

    assert (await client.post(f"{bank}/import", json={"resume_id": str(theirs)})).status_code == 404
    assert (await client.post(f"/applicants/{other}/bank/import", json={})).status_code == 403


# --- owners: which resumes hold an entry (KAN-343, ADR 0005) ----------------------
#
# docs/bank_by_resume.md. An upload holds what it owns; a built resume holds
# what it shows.

OTHER_TEXT = """\
Experience
Harbor Robotics  Jun 2026 - Aug 2026
Mechanical Engineering Intern  Portland, OR
•Designed a sheet-metal bracket that cut assembly time by 20%
Projects
Solar Kart  Jan 2025 - May 2025
•Built a solar go-kart
Skills
•Tools: MATLAB, Python
"""


def _held(saved: dict) -> list[tuple[str, list[str]]]:
    """Each entry's title and skill's name with its resume ids, sorted."""
    return sorted(
        [(e["title"], e["resume_ids"]) for e in saved["entries"]]
        + [(s["name"], s["resume_ids"]) for s in saved["skills"]]
    )


async def test_each_upload_owns_what_it_read_and_shares_nothing(student, upload):
    client, applicant_id, bank = student
    mine = (await client.post(f"{bank}/entries", json={"section": "projects", "title": "Typed by hand"})).json()
    a = (await upload(client, applicant_id, RESUME_TEXT)).json()["id"]
    b = (await upload(client, applicant_id, OTHER_TEXT, filename="resume-b.pdf")).json()["id"]

    saved = (await client.get(bank)).json()
    assert [(r["id"], r["kind"], r["name"], r["primary"]) for r in saved["resumes"]] == [
        (b, "uploaded", "resume-b.pdf", False), (a, "uploaded", "resume.pdf", True),
    ]
    # An upload's table date is its upload time (KAN-361).
    assert all(r["edited_at"] == r["created_at"] for r in saved["resumes"])
    held = _held(saved)
    # The internship and MATLAB are on both uploads: one row each, per upload.
    assert [ids for name, ids in held if name == "Mechanical Engineering Intern"] in ([[a], [b]], [[b], [a]])
    assert sorted(ids[0] for name, ids in held if name == "MATLAB") == sorted([a, b])
    assert ("Budget Buddy", [a]) in held and ("Solar Kart", [b]) in held and ("Python", [b]) in held
    assert (mine["title"], []) in held


async def test_import_again_keeps_one_set_owned_by_the_upload(student, database):
    client, applicant_id, bank = student
    resume_id = str(await _seed_resume(database, applicant_id, RESUME_TEXT))

    for _ in range(2):
        assert (await client.post(f"{bank}/import", json={"resume_id": resume_id})).status_code == 200
    held = _held((await client.get(bank)).json())
    assert len(held) == 8 and all(ids == [resume_id] for _, ids in held)


async def test_an_updated_resume_deletes_what_the_new_file_lacks(student, upload):
    client, applicant_id, bank = student
    a = (await upload(client, applicant_id, RESUME_TEXT)).json()["id"]
    mine = (await client.post(f"{bank}/entries", json={"section": "projects", "title": "Typed by hand"})).json()
    await upload(client, applicant_id, OTHER_TEXT, replacing=a, filename="resume-v2.pdf")

    held = _held((await client.get(bank)).json())
    assert [name for name, _ in held] == [
        "MATLAB", "Mechanical Engineering Intern", "Python", "Solar Kart", mine["title"]]
    assert all(ids == [a] for name, ids in held if name != mine["title"])


async def test_deleting_an_upload_deletes_its_entries_and_skills(student, upload):
    client, applicant_id, bank = student
    mine = (await client.post(f"{bank}/entries", json={"section": "projects", "title": "Typed by hand"})).json()
    a = (await upload(client, applicant_id, RESUME_TEXT)).json()["id"]
    assert (await client.delete(f"/applicants/{applicant_id}/resumes/{a}")).status_code == 200

    saved = (await client.get(bank)).json()
    assert saved["resumes"] == []
    assert ([e["id"] for e in saved["entries"]], saved["skills"]) == ([mine["id"]], [])


async def test_a_built_resume_holds_what_it_shows_and_loses_what_a_replace_deletes(student, upload, database):
    client, applicant_id, bank = student
    a = (await upload(client, applicant_id, RESUME_TEXT)).json()["id"]
    built = (await client.post(f"/applicants/{applicant_id}/built-resumes", json={})).json()["id"]
    saved = (await client.get(bank)).json()
    budget = next(e["id"] for e in saved["entries"] if e["title"] == "Budget Buddy")
    async with database() as session:
        await session.execute(
            text("UPDATE built_resume_entries SET shown = false WHERE built_resume_id = :b AND entry_id = :e"),
            {"b": built, "e": budget},
        )
        await session.commit()

    saved = (await client.get(bank)).json()
    assert [(r["id"], r["kind"]) for r in saved["resumes"]] == [(a, "uploaded"), (built, "base")]
    held = dict(_held(saved))
    assert held["Budget Buddy"] == [a]
    assert held["Mechanical Engineering Intern"] == [a, built]
    assert held["SolidWorks"] == [a, built]

    # A replace deletes the upload's rows, so the built resume shows them no more.
    await client.post(f"{bank}/import", json={"resume_id": a})
    held = dict(_held((await client.get(bank)).json()))
    assert held["Mechanical Engineering Intern"] == [a]


# --- Add under a resume pick (ADR 0005) ----------------------------------------------


async def test_add_under_an_upload_belongs_to_it_and_checks_only_its_entries(student, upload):
    client, applicant_id, bank = student
    a = (await upload(client, applicant_id, RESUME_TEXT)).json()["id"]
    job = {"section": "experience", "title": "Mechanical Engineering Intern", "organization": "Harbor Robotics"}

    # The upload has this job: the duplicate warning, under its pick only.
    res = await client.post(f"{bank}/entries", params={"resume_id": a}, json=job)
    assert res.status_code == 409
    assert (await client.post(f"{bank}/entries", json=job)).status_code == 201

    res = await client.post(f"{bank}/entries", params={"resume_id": a}, json={"section": "projects", "title": "New"})
    assert (res.status_code, res.json()["resume_ids"]) == (201, [a])
    skill = await client.post(f"{bank}/skills", params={"resume_id": a}, json={"name": "Excel"})
    assert (skill.status_code, skill.json()["resume_ids"]) == (201, [a])
    # One name per owner: the upload has SolidWorks, the student's own list does not.
    assert (await client.post(f"{bank}/skills", params={"resume_id": a}, json={"name": "solidworks"})).status_code == 409
    assert (await client.post(f"{bank}/skills", json={"name": "solidworks"})).status_code == 201

    held = dict(_held((await client.get(bank)).json()))
    assert (held["New"], held["Excel"]) == ([a], [a])


async def test_add_under_a_built_resume_shows_it_there(student, upload):
    client, applicant_id, bank = student
    await upload(client, applicant_id, RESUME_TEXT)
    built = (await client.post(f"/applicants/{applicant_id}/built-resumes", json={})).json()["id"]

    res = await client.post(
        f"{bank}/entries", params={"resume_id": built},
        json={"section": "projects", "title": "New", "bullets": ["Did a thing"]},
    )
    assert (res.status_code, res.json()["resume_ids"]) == (201, [built])
    skill = await client.post(f"{bank}/skills", params={"resume_id": built}, json={"name": "Excel"})
    assert (skill.status_code, skill.json()["resume_ids"]) == (201, [built])

    held = dict(_held((await client.get(bank)).json()))
    assert (held["New"], held["Excel"]) == ([built], [built])
    shown = (await client.get(f"/applicants/{applicant_id}/built-resumes/{built}/choices")).json()
    assert res.json()["id"] in {e["entry_id"] for e in shown["entries"] if e["shown"]}


async def test_add_under_another_students_resume_is_not_found(student, database):
    client, _, bank = student
    async with database() as session:
        other = await _seed_applicant(session)
    theirs = await _seed_resume(database, other, RESUME_TEXT)

    res = await client.post(f"{bank}/entries", params={"resume_id": str(theirs)}, json={"section": "projects", "title": "X"})
    assert res.status_code == 404
    assert (await client.get(bank)).json()["entries"] == []


# --- the parse preview and its confirm (KAN-372, ADR 0006) ---------------------------


async def test_a_preview_shows_the_reading_and_saves_nothing(student, upload):
    client, applicant_id, bank = student

    res = await upload(client, applicant_id, RESUME_TEXT, preview=True)
    assert res.status_code == 200
    body = res.json()
    assert [_summary(e) for e in body["entries"]] == [
        ("education", "Riverside State University", None),
        ("experience", "Mechanical Engineering Intern", "Harbor Robotics"),
        ("projects", "Budget Buddy", None),
        ("leadership", "Vice President", "Society of Women Engineers"),
        ("awards", "Dean's List", "Riverside State University"),
        ("certifications", "Certified SolidWorks Associate", None),
    ]
    assert body["entries"][1]["bullets"] == [
        "Designed a sheet-metal bracket that cut assembly time by 20%",
        "Ran tolerance stack-up analyses in SolidWorks",
    ]
    assert [(s["name"], s["group"]) for s in body["skills"]] == [("SolidWorks", "Tools"), ("MATLAB", "Tools")]
    assert body["duplicate_of"] is None

    # Nothing kept: no file, no resume row, no bank rows.
    assert upload.bucket.files == {}
    assert (await client.get(f"/applicants/{applicant_id}/resumes")).json() == []
    saved = (await client.get(bank)).json()
    assert (saved["entries"], saved["skills"]) == ([], [])


async def test_a_preview_of_an_uploaded_resume_names_the_upload(student, upload):
    client, applicant_id, _ = student
    first = (await upload(client, applicant_id, RESUME_TEXT, filename="Sam 2026.pdf")).json()

    body = (await upload(client, applicant_id, RESUME_TEXT, preview=True)).json()
    assert body["duplicate_of"] == {"resume_id": first["id"], "name": "Sam 2026.pdf"}


async def test_a_preview_marks_what_a_confirm_replaces_from_earlier_uploads_only(student, upload):
    client, applicant_id, bank = student
    old = (await upload(client, applicant_id, RESUME_TEXT)).json()["id"]
    saved = (await client.get(bank)).json()
    old_job = next(e["id"] for e in saved["entries"] if e["section"] == "experience")
    old_matlab = next(s["id"] for s in saved["skills"] if s["name"] == "MATLAB")
    # Typed by hand, the same job: never replaced.
    await client.post(
        f"{bank}/entries",
        json={"section": "experience", "title": "mechanical engineering intern", "organization": "harbor robotics"},
    )

    body = (await upload(client, applicant_id, OTHER_TEXT, preview=True)).json()
    assert [(e["title"], e["replaces"]) for e in body["entries"]] == [
        ("Mechanical Engineering Intern", [old_job]), ("Solar Kart", []),
    ]
    assert [(s["name"], s["replaces"]) for s in body["skills"]] == [("MATLAB", [old_matlab]), ("Python", [])]
    assert old in {r["id"] for r in saved["resumes"]}


async def test_a_confirmed_preview_replaces_matching_entries_instead_of_adding_copies(student, upload):
    client, applicant_id, bank = student
    old = (await upload(client, applicant_id, RESUME_TEXT)).json()["id"]
    await client.post(
        f"{bank}/entries",
        json={"section": "experience", "title": "mechanical engineering intern", "organization": "harbor robotics"},
    )

    res = await upload(client, applicant_id, OTHER_TEXT, filename="resume-b.pdf", replace_matching=True)
    assert res.status_code == 200
    new = res.json()["id"]
    assert res.json()["bank"] == {
        "found": 4, "entries_added": 2, "skills_added": 2, "entries_replaced": 1, "skills_replaced": 1,
        "read_by": "parser", "uses_left": 1,
    }

    held = _held((await client.get(bank)).json())
    # One internship and one MATLAB from the uploads, now the newer one's;
    # the older upload keeps what the newer one does not list; the
    # student's own entry stays.
    assert [ids for name, ids in held if name == "Mechanical Engineering Intern"] == [[new]]
    assert [ids for name, ids in held if name == "MATLAB"] == [[new]]
    assert ("Budget Buddy", [old]) in held and ("SolidWorks", [old]) in held
    assert ("mechanical engineering intern", []) in held

    # A third version, confirmed the same way, still leaves one of each.
    newer = OTHER_TEXT.replace("Built a solar go-kart", "Built and raced a solar go-kart")
    assert (await upload(client, applicant_id, newer, filename="resume-c.pdf", replace_matching=True)).status_code == 200
    held = _held((await client.get(bank)).json())
    assert [name for name, _ in held].count("Solar Kart") == 1
    assert [name for name, _ in held].count("MATLAB") == 1


async def test_another_students_preview_is_refused(student, upload, database):
    client, _, _ = student
    async with database() as session:
        other = await _seed_applicant(session)
    assert (await upload(client, other, RESUME_TEXT, preview=True)).status_code == 403


# --- reading with the model (KAN-222, KAN-732, ADR 0007) ------------------------------
#
# ScriptedLLM stands in for the model (seam 2); its script is the model's JSON.
# Every reading asks it first while a use is left; the parser reads behind it.

# Starts with a contact block, which the model is never sent.
MODEL_TEXT = """\
Samantha J. Seeker
12 Elm Street, Riverside, CA | sam.seeker@example.com | (631) 555-0142
Experience
Riverside Materials Lab  Jan 2025 - Present
Lab Assistant  Riverside, CA
•Prepared tensile test samples
•Logged results in Excel
Projects
Wind Tunnel  May 2025 - Aug 2025
https://github.com/example/wind-tunnel
•Built a small wind tunnel
Education
Riverside State University  Expected May 2099
B.S. in Mechanical Engineering
•GPA: 3.50
Skills
•Tools: Excel, MATLAB
"""

MODEL_READING = {
    "entries": [
        {
            "section": "experience",
            "title": "Lab Assistant",
            "organization": "Riverside Materials Lab",
            "location": "Riverside, CA",
            "start_month": "2025-01",
            "end_month": None,
            "end_kind": "present",
            # Not the resume's: its number is nowhere in the text.
            "bullets": ["Prepared tensile test samples", "Logged results in Excel", "Cut testing costs by 35%"],
        },
        # Not on the resume at all: its title goes, and the entry with it.
        {"section": "experience", "title": "Research Intern", "organization": "NASA Ames",
         "bullets": ["Simulated airflow over wings"]},
        # An end before the start: kept, without its dates. No link: the
        # model sees every URL as [link], so the parser's is taken.
        {"section": "projects", "title": "Wind Tunnel", "start_month": "2025-08", "end_month": "2025-05",
         "end_kind": "month", "bullets": ["Built a small wind tunnel"]},
        # No title: not an entry, dropped.
        {"section": "awards", "title": ""},
        # A field the model saw only as a placeholder is never filled with it.
        {"section": "education", "title": "Riverside State University", "degree": "B.S.", "field_of_study": "[link]",
         "gpa": 3.5},
    ],
    # "excel" is Excel again; Python is not on the resume.
    "skills": [{"name": "Excel", "group": "Tools"}, {"name": "excel", "group": None}, {"name": "Python", "group": None}],
}

# Text the heuristic parser finds no section in.
UNREADABLE_TEXT = "Sam Seeker\nsam.seeker@example.com\n(631) 555-0142\nlinkedin.com/in/samseeker\nLab Assistant at Riverside Materials Lab since January 2025."


@pytest.fixture
def parsing_caps(monkeypatch):
    """Set the parsing cap and the daily pool for one test."""

    def set_caps(*, cap: int | None = None, pool: int | None = None):
        if cap is not None:
            monkeypatch.setattr(get_settings(), "ai_parsing_cap", cap)
        if pool is not None:
            monkeypatch.setattr(get_settings(), "ai_daily_pool", pool)

    return set_caps


@pytest.fixture
def use_model():
    def install(*scripts) -> ScriptedLLM:
        fake = ScriptedLLM(*scripts)
        fake_models.use(fake)
        return fake

    yield install
    fake_models.clear()


def rate_limited() -> RateLimitError:
    request = httpx.Request("POST", "http://endpoint.test/v1/chat/completions")
    return RateLimitError("quota", response=httpx.Response(429, request=request), body=None)


def _reading(data: dict = MODEL_READING) -> list[str]:
    return [json.dumps(data)]


def _confirming(preview: dict) -> str:
    """The `reading` a confirm sends: the preview's entries, skills and reader."""
    return json.dumps({"entries": preview["entries"], "skills": preview["skills"], "read_by": preview["read_by"]})


async def test_an_upload_is_read_by_the_model_and_checked_against_its_text(student, upload, use_model):
    client, applicant_id, bank = student
    use_model(_reading())

    res = await upload(client, applicant_id, MODEL_TEXT)
    assert res.status_code == 200
    assert res.json()["bank"] == {
        "found": 4, "entries_added": 3, "skills_added": 1, "entries_replaced": 0, "skills_replaced": 0,
        "read_by": "model", "uses_left": 0,
    }

    saved = (await client.get(bank)).json()
    school, lab, tunnel = saved["entries"]
    assert _summary(lab) == ("experience", "Lab Assistant", "Riverside Materials Lab")
    assert (lab["start_month"], lab["end_kind"], [b["text"] for b in lab["bullets"]]) == (
        "2025-01", "present", ["Prepared tensile test samples", "Logged results in Excel"],
    )
    assert (tunnel["title"], tunnel["start_month"], tunnel["end_month"]) == ("Wind Tunnel", None, None)
    assert tunnel["link"] == "https://github.com/example/wind-tunnel"
    assert (school["degree"], school["field_of_study"], school["gpa"]) == ("B.S.", None, 3.5)
    assert [(s["name"], s["group"]) for s in saved["skills"]] == [("Excel", "Tools")]


async def test_the_model_gets_no_identity_data_and_no_contact_block(student, upload, use_model, database):
    client, applicant_id, _ = student
    async with database() as session:
        await session.execute(
            text("UPDATE applicant_profiles SET phone_number = '631-555-0142', linkedin_url = 'https://linkedin.com/in/samseeker' WHERE id = :id"),
            {"id": applicant_id},
        )
        await session.commit()
    fake = use_model(_reading())

    await upload(client, applicant_id, MODEL_TEXT)
    sent = json.dumps(fake.prompts)
    # The header goes whole, with a name the profile spells otherwise.
    for secret in ("Samantha", "Seeker", "Elm Street", "sam.seeker@example.com", "555-0142", "github.com/example"):
        assert secret not in sent
    assert "Riverside Materials Lab" in sent


@pytest.mark.parametrize("script", [lambda: ["not json"], rate_limited], ids=["wrong shape", "out of quota"])
async def test_a_model_that_fails_leaves_the_parsers_reading_and_counts_nothing(student, upload, use_model, script):
    client, applicant_id, bank = student
    use_model(script())

    res = await upload(client, applicant_id, MODEL_TEXT)
    assert res.status_code == 200
    body = res.json()["bank"]
    assert (body["read_by"], body["uses_left"], body["found"]) == ("parser", 1, 5)
    titles = [e["title"] for e in (await client.get(bank)).json()["entries"]]
    assert titles == ["Riverside State University", "Lab Assistant", "Wind Tunnel"]


async def test_at_the_parsing_cap_the_parser_reads_without_asking_the_model(student, upload, use_model, parsing_caps):
    client, applicant_id, _ = student
    parsing_caps(cap=1)
    fake = use_model(_reading())

    assert (await upload(client, applicant_id, MODEL_TEXT)).json()["bank"]["read_by"] == "model"
    body = (await upload(client, applicant_id, OTHER_TEXT, filename="resume-b.pdf")).json()["bank"]
    assert (body["read_by"], body["uses_left"]) == ("parser", 0)
    assert len(fake.prompts) == 1


async def test_parsing_stops_when_its_share_of_the_pool_is_spent(student, upload, use_model, parsing_caps, database):
    client, applicant_id, _ = student
    parsing_caps(pool=10)  # parsing's 10% share: one use across all students
    use_model(_reading())
    assert (await upload(client, applicant_id, MODEL_TEXT)).json()["bank"]["read_by"] == "model"

    async with database() as session:
        other = await _seed_applicant(session)
    _sign_in(other)
    body = (await upload(client, other, MODEL_TEXT)).json()["bank"]
    assert (body["read_by"], body["uses_left"]) == ("parser", 0)


async def test_a_confirm_saves_the_previews_reading_without_reading_again(student, upload, use_model):
    client, applicant_id, bank = student
    fake = use_model(_reading())

    preview = (await upload(client, applicant_id, MODEL_TEXT, preview=True)).json()
    assert preview["read_by"] == "model"
    assert [e["title"] for e in preview["entries"]] == ["Lab Assistant", "Wind Tunnel", "Riverside State University"]

    res = await upload(client, applicant_id, MODEL_TEXT, replace_matching=True, reading=_confirming(preview))
    assert res.status_code == 200
    # The preview spent the day's one reading; the confirm asked no model.
    assert (res.json()["bank"]["read_by"], res.json()["bank"]["uses_left"]) == ("model", 0)
    assert len(fake.prompts) == 1
    saved = (await client.get(bank)).json()
    assert [e["title"] for e in saved["entries"]] == ["Riverside State University", "Lab Assistant", "Wind Tunnel"]
    assert [s["name"] for s in saved["skills"]] == ["Excel"]


async def test_a_confirmed_reading_that_is_not_one_is_refused_before_anything_is_kept(student, upload):
    client, applicant_id, _ = student
    res = await upload(client, applicant_id, MODEL_TEXT, replace_matching=True, reading='{"entries": [{"title": ""}]}')
    assert res.status_code == 422
    assert upload.bucket.files == {}
    assert (await client.get(f"/applicants/{applicant_id}/resumes")).json() == []


async def test_an_updated_resume_is_read_by_the_model_too(student, upload, use_model):
    client, applicant_id, _ = student
    first = (await upload(client, applicant_id, RESUME_TEXT)).json()
    assert first["bank"]["read_by"] == "parser"

    use_model(_reading())
    res = await upload(client, applicant_id, MODEL_TEXT, replacing=first["id"])
    assert (res.json()["bank"]["read_by"], res.json()["bank"]["entries_added"]) == ("model", 3)


async def test_import_again_reads_with_the_model_first(student, database, use_model):
    client, applicant_id, bank = student
    resume_id = await _seed_resume(database, applicant_id, MODEL_TEXT)
    use_model(_reading())

    res = await client.post(f"{bank}/import", json={"resume_id": str(resume_id)})
    assert res.status_code == 200
    body = res.json()
    assert (body["read_by"], body["uses_left"], _counts(body)) == ("model", 0, (3, 1))
    # The next reading today is the parser's, and still succeeds.
    body = (await client.post(f"{bank}/import", json={"resume_id": str(resume_id)})).json()
    assert (body["read_by"], body["uses_left"], _counts(body)) == ("parser", 0, (3, 2))


def test_a_model_field_the_resume_lacks_is_removed():
    # Pure, no database: what `_backed` lets through and what it takes out.
    from app.schemas.bank import ModelReading
    from app.services.bank_import import model_drafts

    text = (
        "Experience\nHarbor Robotics  Jun 2026 - Aug 2026\nMechanical Engineering Intern\n"
        "•Designed a sheet-metal bracket that cut assem bly time by 20%\n"
        "Education\nRiverside State University  B.S.  GPA: 3.80\n"
    )
    reading = ModelReading.model_validate({"entries": [
        {"section": "experience", "title": "Mechanical Engineering Intern", "organization": "Harbor Robotics",
         "start_month": "2026-06", "end_month": "2026-08", "end_kind": "month",
         "bullets": [
             # The PDF broke "assembly" in two: three words in four still pass.
             "Designed a sheet-metal bracket that cut assembly time by 20%",
             # A number the resume lacks fails, however many words match.
             "Designed a sheet-metal bracket that cut assembly time by 40%",
         ]},
        # A short field needs every word: the resume says "B.S.", not this.
        {"section": "education", "title": "Riverside State University", "degree": "Bachelor of Science",
         "gpa": 3.8, "gpa_scale": 4.0, "start_month": "2019-09", "end_month": "2099-05", "end_kind": "expected"},
    ]})
    job, school = model_drafts(reading, text)
    assert job.bullets == ["Designed a sheet-metal bracket that cut assembly time by 20%"]
    assert (job.start_month.isoformat(), job.end_month.isoformat()) == ("2026-06-01", "2026-08-01")
    # 3.8 is the resume's "3.80"; a year it lacks (2019) takes every date.
    assert (school.degree, school.gpa, school.gpa_scale) == (None, 3.8, 4.0)
    assert (school.start_month, school.end_month, school.end_kind) == (None, None, None)


def test_the_model_is_sent_the_text_from_the_first_heading_near_the_top():
    from app.services.bank_import import _from_first_heading

    assert _from_first_heading("Sam\n12 Elm St\nEducation\nRiverside") == "Education\nRiverside"
    # A first heading far down could follow entries the parser cannot name: all goes.
    deep = "\n".join(["line"] * 12 + ["Education", "Riverside"])
    assert _from_first_heading(deep) == deep


def test_a_model_project_takes_the_parsers_link_by_its_title():
    from app.schemas.bank import DraftEntry
    from app.services.bank_import import with_links

    parsed = [
        DraftEntry(section="projects", title="Line Robot | Robotics Club", link="https://example.com/robot"),
        DraftEntry(section="projects", title="Budget Buddy", link="https://example.com/budget"),
    ]
    drafts = [
        DraftEntry(section="projects", title="Line Robot"),
        DraftEntry(section="projects", title="budget buddy"),
        DraftEntry(section="projects", title="Line"),  # "Line" is not the first word of a title alone
        DraftEntry(section="experience", title="Budget Buddy"),
    ]
    assert [d.link for d in with_links(drafts, parsed)] == [
        "https://example.com/robot", "https://example.com/budget", None, None,
    ]


async def test_a_model_slower_than_the_wait_leaves_the_parsers_reading(monkeypatch):
    import asyncio

    from workit_scout.identity import Identity

    from app.services import bank_import

    async def slow(raw_text, llm, *, identity):
        await asyncio.sleep(5)

    monkeypatch.setattr(bank_import, "read_with_model", slow)
    monkeypatch.setattr(bank_import, "MODEL_WAIT_SECONDS", 0.01)
    reading = await bank_import.read_resume(RESUME_TEXT, ScriptedLLM(["{}"]), Identity(name="Sam Seeker"))
    assert reading.read_by == "parser"
    assert len(reading.entries) == 6


async def test_a_model_reading_the_text_backs_none_of_leaves_the_parsers():
    from workit_scout.identity import Identity

    from app.services.bank_import import read_resume

    invented = {"entries": [{"section": "experience", "title": "Astronaut", "organization": "NASA"}]}
    reading = await read_resume(RESUME_TEXT, ScriptedLLM(_reading(invented)), Identity(name="Sam Seeker"))
    assert (reading.read_by, len(reading.entries)) == ("parser", 6)


async def test_a_bullet_the_seam_put_a_placeholder_in_takes_the_parsers_words():
    # Found reading the shared test account, named Test User: the seam took
    # "user" out of "user stories" as a part of the name, and the model gave
    # "[name] stories" back.
    from workit_scout.identity import Identity

    from app.services.bank_import import read_resume

    text = (
        "Experience\nPulp  Jan 2025 - Aug 2025\nProduct Intern  Remote\n"
        "•Translated research findings into PRDs and user stories for 20 contributors\n"
    )
    reply = {"entries": [{"section": "experience", "title": "Product Intern", "organization": "Pulp", "bullets": [
        "Translated research findings into PRDs and [name] stories for 20 contributors",
        # No line of the resume says this: it goes, never saved with "[name]".
        "Presented to [name] weekly",
    ]}]}
    fake = ScriptedLLM(_reading(reply))
    reading = await read_resume(text, fake, Identity(name="Test User"))
    assert "[name] stories" in json.dumps(fake.prompts)
    assert reading.read_by == "model"
    assert reading.entries[0].bullets == ["Translated research findings into PRDs and user stories for 20 contributors"]


def test_the_reading_keeps_the_gpa_scale_and_project_tools():
    # Pure, no database: "GPA: 3.62/4.00" fills the scale, and a project's
    # "| C++, CMake" tools become ungrouped skills after the skills section's own.
    entries, skills = read(
        "Education\nLakeview University  Expected Graduation: May 2099\n"
        "Bachelor of Science, Computer Science  GPA: 3.62/4.00\n"
        "Projects\nLine Robot| C++, CMake\n• Built a robot.\n"
        "Skills\nLanguages: C++, Python\n"
    )
    school = entries[0]
    assert (school.title, school.degree, school.field_of_study, school.gpa, school.gpa_scale) == (
        "Lakeview University", "Bachelor of Science", "Computer Science", 3.62, 4.0,
    )
    assert skills == [("C++", "Languages"), ("Python", "Languages"), ("CMake", None)]


def test_a_titles_tool_list_after_a_bar_is_split_off_and_never_glued_onto_a_skill():
    # Pure, no database: "Role| C++, Go  City, ST" under a "Company  Dates" line
    # keeps only the role; the tools join the skills, ungrouped, after the
    # skills section's own. A project's "Name | Group| C++, Go" takes the
    # last bar's list, so the group never becomes part of a skill.
    entries, skills = read(
        "Experience\n"
        "Northwind Signals  Jun 2098 – Aug 2098\n"
        "Software Engineer Intern, Telemetry| C++, Go, gRPC  Springfield, IL\n"
        "• Built a thing.\n"
        "Bluebird Labs  Jan 2099 – Present\n"
        "Software Engineer (Part-Time)| Ruby, Rails  Remote\n"
        "• Built another thing.\n"
        "Projects\n"
        "Line Robot  | Robotics Club| C/C++, Arduino  Aug 2097 – Present\n"
        "• Built a robot.\n"
        "Skills\nLanguages: C++, Go\n"
    )
    jobs = [(e.title, e.organization, e.location) for e in entries if e.section.value == "experience"]
    assert jobs == [
        ("Software Engineer Intern, Telemetry", "Northwind Signals", "Springfield, IL"),
        ("Software Engineer (Part-Time)", "Bluebird Labs", "Remote"),
    ]
    assert [e.title for e in entries if e.section.value == "projects"] == ["Line Robot | Robotics Club"]
    assert skills == [
        ("C++", "Languages"), ("Go", "Languages"),
        ("gRPC", None), ("Ruby", None), ("Rails", None), ("C/C++", None), ("Arduino", None),
    ]


def test_a_reading_never_keeps_a_qualification_or_a_glued_name_as_a_skill():
    pairs = [("Rust", "Languages"), ("Robotics Club| C++", None), ("Computer Science degree", None),
             ("AI tools", None), ("3+ years of Java", None), ("Docker", "Tools")]
    assert skill_pairs(pairs) == [("Rust", "Languages"), ("Docker", "Tools")]


def test_a_reading_keeps_only_catalog_skills_in_the_resumes_spelling_once_each():
    pairs = [("ReactJS", "Frameworks"), ("Teamwork", None), ("Communication", None), ("Python", None),
             ("Leadership", None), ("REST APIs", None), ("React", None), ("Pi Pico", None),
             ("Microsoft Office Tools", None), ("Problem Solving", None)]
    assert skill_pairs(pairs) == [("ReactJS", "Frameworks"), ("Python", None), ("REST APIs", None),
                                  ("Pi Pico", None), ("Microsoft Office Tools", None)]


def test_a_model_reading_with_null_lists_still_counts():
    # Groq's gpt-oss sends coursework: null on a job. That is an empty list,
    # not a failed reading.
    from app.schemas.bank import ModelReading
    from app.services.bank_import import model_drafts

    reading = ModelReading.model_validate({
        "entries": [{"section": "experience", "title": "Intern", "organization": "Acme",
                     "coursework": None, "bullets": ["Built  a tool."]}],
        "skills": None,
    })
    assert [(d.title, d.coursework, d.bullets) for d in model_drafts(reading)] == [
        ("Intern", [], ["Built a tool."]),
    ]


# --- Rename (KAN-268) -----------------------------------------------------------


async def test_a_rename_keeps_the_files_extension(student, database):
    client, applicant_id, _ = student
    resume_id = await _seed_resume(database, applicant_id, RESUME_TEXT)
    url = f"/applicants/{applicant_id}/resumes/{resume_id}"

    res = await client.patch(url, json={"name": "  Mechanical  "})
    assert (res.status_code, res.json()["original_filename"]) == (200, "Mechanical.pdf")
    # A name that already ends in it is left as typed, in any case.
    res = await client.patch(url, json={"name": "Final.PDF"})
    assert res.json()["original_filename"] == "Final.PDF"
    assert (await client.get(url)).json()["original_filename"] == "Final.PDF"


async def test_a_rename_refuses_a_blank_name_and_another_students_resume(student, database):
    client, applicant_id, _ = student
    resume_id = await _seed_resume(database, applicant_id, RESUME_TEXT)
    async with database() as session:
        other = await _seed_applicant(session)
    theirs = await _seed_resume(database, other, RESUME_TEXT)

    blank = await client.patch(f"/applicants/{applicant_id}/resumes/{resume_id}", json={"name": "  "})
    assert blank.status_code == 422
    stolen = await client.patch(f"/applicants/{applicant_id}/resumes/{theirs}", json={"name": "Mine"})
    assert stolen.status_code == 404
    assert (await client.get(f"/applicants/{applicant_id}/resumes/{resume_id}")).json()["original_filename"] == "resume.pdf"


# --- A removed skill stays removed (KAN-369) ----------------------------------


def _skill_names(saved: dict) -> list[str]:
    return sorted(s["name"] for s in saved["skills"])


async def test_a_skill_the_student_deletes_is_never_read_in_again_until_they_add_it(student, upload, database):
    client, applicant_id, bank = student
    resume_id = await _seed_resume(database, applicant_id, RESUME_TEXT)
    await client.post(f"{bank}/import", json={"resume_id": str(resume_id)})
    matlab = next(s for s in (await client.get(bank)).json()["skills"] if s["name"] == "MATLAB")

    assert (await client.delete(f"{bank}/skills/{matlab['id']}")).status_code == 204
    await client.post(f"{bank}/import", json={"resume_id": str(resume_id)})
    assert _skill_names((await client.get(bank)).json()) == ["SolidWorks"]
    preview = (await upload(client, applicant_id, OTHER_TEXT, preview=True)).json()
    assert [s["name"] for s in preview["skills"]] == ["Python"]

    # Added by hand, it is the student's again, and readings may add it.
    assert (await client.post(f"{bank}/skills", json={"name": "Matlab"})).status_code == 201
    await client.post(f"{bank}/import", json={"resume_id": str(resume_id)})
    assert _skill_names((await client.get(bank)).json()) == ["MATLAB", "Matlab", "SolidWorks"]


async def test_a_skill_removed_in_the_preview_is_not_saved_or_read_in_later(student, upload):
    client, applicant_id, bank = student
    res = await upload(client, applicant_id, RESUME_TEXT, replace_matching=True, removed_skills=["SolidWorks"])
    assert res.status_code == 200, res.text
    resume_id = res.json()["id"]
    assert _skill_names((await client.get(bank)).json()) == ["MATLAB"]

    await client.post(f"{bank}/import", json={"resume_id": resume_id})
    assert _skill_names((await client.get(bank)).json()) == ["MATLAB"]
