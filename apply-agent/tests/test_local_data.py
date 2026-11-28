"""W11: WorkIt Auto Apply keeps nothing of an application on the Mac once it is done. What the form sent goes to
WorkIt with the applied write, the Sent resume is named by its id, and the Record, trace, files and Tracker go."""

from datetime import date
from pathlib import Path

import pytest

from apply import batch, build, local_data, tailored, trace, verify
from apply.keychain import InMemoryKeychain
from apply.model import Posting, Question
from apply.records import Filled, Record
from apply.rehearsal import sent_answers
from apply.tracker import (
    ACCOUNT_LIST,
    EmployerAccount,
    FileTracker,
    KeychainTracker,
    accounts_in,
)
from apply.workit import Stage, WaitingWrites, Write

POSTING = Posting("app-7", "Acme", "Intern", "https://job-boards.greenhouse.io/acme/jobs/7")


def test_what_a_form_sent_is_its_page_answers_with_each_essays_text_and_never_a_secret():
    """Fault: a password went to WorkIt, an empty answer was kept, a file went by its path, the cover letter went as
    a file name, or an AI answer wasn't marked."""
    questions = [Question("name", "First Name", "text"), Question("pw", "Create a password", "text"),
                 Question("tools", "Tools you've used", "checkbox"), Question("why", "Why Acme?", "textarea"),
                 Question("cl", "Cover Letter", "file"), Question("blank", "Middle Name", "text"),
                 Question("heard", "How did you hear about us?", "text")]
    record = Record(POSTING, None, "", Filled(
        questions, answers={"name": "Sam", "pw": "hunter2", "cl": Path("/Users/sam/Sam_Cover_Letter.pdf"),
                            "heard": "WorkIt"},
        readback={"name": "Sam", "pw": "hunter2", "tools": ["Git", "Docker"], "why": "Trains.", "blank": ""},
        screenshot=b""), date(2026, 11, 27),
        essays="## Why Acme?\nI rode their trains.\n\n## Cover Letter\nDear Acme, ...",
        drafted=(("How did you hear about us?", "WorkIt"),))

    assert sent_answers(record) == [
        {"question": "First Name", "answer": "Sam", "ai": False},
        {"question": "Tools you've used", "answer": ["Git", "Docker"], "ai": False},
        {"question": "Why Acme?", "answer": "I rode their trains.", "ai": True},
        {"question": "Cover Letter", "answer": "Dear Acme, ...", "ai": True},
        {"question": "How did you hear about us?", "answer": "WorkIt", "ai": True},
    ]


class Client:
    def __init__(self):
        self.applied = []

    def record_applied(self, link, company, title, resume=None, resume_ref=None, answers=None):
        self.applied.append((link, resume, resume_ref, answers))

    def add_by_link(self, link, company, title):
        return "job-8", None

    def applicant_id(self):
        return "me"

    def set_stage(self, me, job, stage):
        pass


def test_an_applied_write_carries_the_resume_id_and_the_answers_and_its_delivery_forgets_the_application(tmp_path):
    """Fault: the Sent resume needed a file copy, the answers never reached WorkIt, or the Mac's files went before
    WorkIt had them (a write that waits keeps them)."""
    client, forgot = Client(), []
    writes = WaitingWrites(client, tmp_path / "queue.json", delivered=forgot.append)
    write = Write("app-7", POSTING.url, "Acme", "Intern", Stage.APPLIED, resume_ref={"built_resume_id": "b1"},
                  answers=[{"question": "Why Acme?", "answer": "Trains.", "ai": True}])

    writes.send(write)
    writes.send(Write("app-8", POSTING.url, "Acme", "Intern", Stage.NEEDS_YOU))

    assert client.applied == [(POSTING.url, None, {"built_resume_id": "b1"}, write.answers)]
    assert [w.application_id for w in forgot] == ["app-7"]  # a held form's needs-you write forgets nothing


@pytest.fixture
def mac(tmp_path, monkeypatch):
    """A data folder with one sent Application's files and one open form's."""
    monkeypatch.setattr(build, "STUDENT", True)
    for module, name, path in ((local_data, "HOME", tmp_path), (local_data, "RECORDS", tmp_path / "rehearsals"),
                               (local_data, "SENT", tmp_path / "sent"), (local_data, "TAILORED", tmp_path / "tailored"),
                               (local_data, "FILES", tmp_path / "files"), (trace, "TRACES", tmp_path / "traces"),
                               (batch, "PATH", tmp_path / "open-forms.json"),
                               (verify, "DISMISSED", tmp_path / "dismissed-flags.json")):
        monkeypatch.setattr(module, name, path)
    for company, app in (("Acme", "app-7"), ("Beta", "app-9")):
        for path in (tmp_path / "rehearsals/2026-11-27" / f"{company.lower()}-{app}/form.png",
                     tmp_path / "sent/2026-11-27" / local_data.sent_name(company, app) / "Sam_Resume.pdf",
                     tmp_path / "tailored" / app / "Sam_Resume.pdf", tmp_path / "traces/2026-11-27" / f"{app}.jsonl"):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x")
        verify.dismiss(app, "Phone", "looks short")
    (tmp_path / "files").mkdir()
    (tmp_path / "files/Sam_Resume.pdf").write_text("x")
    batch.note("https://jobs.lever.co/beta/9", application_id="app-9", company="Beta")  # still open
    return tmp_path


def test_a_sent_applications_files_go_and_an_open_forms_stay(mac):
    """Fault: a Record, trace, tailored resume, file copy or dismissed flag of a sent form stayed on the Mac, or an
    open form lost one (a restart brings it back)."""
    local_data.forget("Acme", "app-7")

    left = sorted(str(p.relative_to(mac)) for p in mac.rglob("*") if p.is_file())
    assert not [p for p in left if "app-7" in p]
    assert any("rehearsals" in p and "app-9" in p for p in left) and verify.dismissed("app-9")
    assert not verify.dismissed("app-7")


def test_the_app_opens_with_only_open_forms_files_and_an_older_trackers_accounts_in_the_keychain(mac):
    """Fault: a crash's or an older version's files stayed, the profile's file copies stayed past a run, or the older
    tracker.json went with its Employer accounts (the app would make the same account again)."""
    FileTracker(mac / "tracker.json").add_employer_account(
        EmployerAccount("Acme", "acme.wd1.myworkdayjobs.com", "sam@example.com", date(2026, 11, 2)))
    keychain = InMemoryKeychain()

    local_data.sweep(keychain)

    left = sorted(str(p.relative_to(mac)) for p in mac.rglob("*") if p.is_file())
    assert not [p for p in left if "app-7" in p or p.startswith(("files", "tracker"))]
    assert [a.site for a in accounts_in(keychain)] == ["acme.wd1.myworkdayjobs.com"]
    assert any("app-9" in p for p in left)


def test_the_apps_tracker_keeps_its_accounts_in_the_keychain_and_its_rows_in_memory(tmp_path):
    """Fault: an account made on one launch was gone on the next, or the Tracker wrote a file."""
    keychain = InMemoryKeychain()
    KeychainTracker(keychain).add_employer_account(EmployerAccount("Acme", "a.example.com", "s@x.com", date(2026, 11, 27)))
    KeychainTracker(keychain).add_employer_account(EmployerAccount("Beta", "b.example.com", "s@x.com", date(2026, 11, 27)))

    assert [a.site for a in KeychainTracker(keychain).employer_accounts()] == ["a.example.com", "b.example.com"]
    assert keychain.password(ACCOUNT_LIST) and not list(tmp_path.iterdir())


def test_the_tailored_resume_is_deleted_once_the_form_has_it_and_named_by_its_id(tmp_path):
    """Fault: the tailored PDF stayed on the Mac after its upload, or its Sent resume had no id to name it by."""
    class WorkIt:
        def logged_in(self):
            return True

        def tailored_resume(self, url):
            return b"%PDF tailored", "built-3"

    from apply.profile import ApplicantProfile
    profile = ApplicantProfile({"files": {"resume_pdf": str(tmp_path / "Sam_Resume.pdf")}}, tmp_path, {})
    given = tailored.resume_for(POSTING, profile, tailored.from_workit(WorkIt()), tmp_path / "tailored")
    path = Path(given.get(tailored.RESUME))

    assert path.read_bytes() == b"%PDF tailored" and tailored.GIVEN.pop("app-7") == {"built_resume_id": "built-3"}
    tailored.forget(given)
    assert not path.exists()


def test_what_the_form_showed_at_the_press_wins_and_an_edited_ai_answer_is_no_longer_marked_ai():
    """Fault: an edit the student made on the held form was lost (the Record's fill-time answer went instead), an
    essay they rewrote stayed marked as AI's, or a cover letter upload went as its file's path."""
    questions = [Question("why", "Why Acme?", "textarea"), Question("heard", "How did you hear about us?", "text"),
                 Question("year", "Graduation year", "select"), Question("cl", "Cover Letter", "file")]
    record = Record(POSTING, None, "", Filled(
        questions, answers={"heard": "WorkIt", "year": "2027", "cl": Path("/Users/sam/Sam_Cover_Letter.pdf")},
        readback={"year": "2027"}, screenshot=b""), date(2026, 11, 27),
        essays="## Why Acme?\nI rode their trains.\n\n## Cover Letter\nDear Acme, ...",
        drafted=(("How did you hear about us?", "WorkIt"),))
    shown = {"why": "I rode their trains every day for four years.", "heard": "WorkIt", "year": "2028",
             "cl": "C:\\fakepath\\Sam_Cover_Letter.pdf"}

    assert sent_answers(record, shown) == [
        {"question": "Why Acme?", "answer": "I rode their trains every day for four years.", "ai": False},
        {"question": "How did you hear about us?", "answer": "WorkIt", "ai": True},
        {"question": "Graduation year", "answer": "2028", "ai": False},
        {"question": "Cover Letter", "answer": "Dear Acme, ...", "ai": True},
    ]
