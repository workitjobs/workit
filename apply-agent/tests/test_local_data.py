"""W11: WorkIt Auto Apply keeps nothing of an application on the Mac once it is done. What the form sent goes to
WorkIt with the applied write, the Sent resume is named by its id, and the Record, trace, files and Tracker go."""

import json
from datetime import date
from pathlib import Path

import pytest

from apply import (
    already_applied,
    batch,
    build,
    local_data,
    other_roles,
    sent_capture,
    student,
    tailored,
    trace,
    tracker,
    verify,
)
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
from apply.workit import Stage, Unreachable, WaitingWrites, WorkIt, WorkItError, Write

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
    essay they rewrote stayed marked as AI's, an AI answer they cleared went as sent, a resume they swapped for their
    own went as WorkIt's, or a cover letter upload went as its file's path."""
    questions = [Question("why", "Why Acme?", "textarea"), Question("heard", "How did you hear about us?", "text"),
                 Question("year", "Graduation year", "select"), Question("cl", "Cover Letter", "file"),
                 Question("extra", "Anything else?", "textarea"), Question("resume", "Resume", "file")]
    record = Record(POSTING, None, "", Filled(
        questions, answers={"heard": "WorkIt", "year": "2027", "cl": Path("/Users/sam/Sam_Cover_Letter.pdf"),
                            "extra": "Happy to relocate.", "resume": Path("/Users/sam/Sam_Resume.pdf")},
        readback={"year": "2027", "extra": "Happy to relocate."}, screenshot=b""), date(2026, 11, 27),
        essays="## Why Acme?\nI rode their trains.\n\n## Cover Letter\nDear Acme, ...",
        drafted=(("How did you hear about us?", "WorkIt"), ("Anything else?", "Happy to relocate.")))
    shown = {"why": "I rode their trains every day for four years.", "heard": "WorkIt", "year": "2028",
             "cl": "C:\\fakepath\\Sam_Cover_Letter.pdf", "extra": "", "resume": "C:\\fakepath\\Sam_Own_Resume.pdf"}

    assert sent_answers(record, shown) == [
        {"question": "Why Acme?", "answer": "I rode their trains every day for four years.", "ai": False},
        {"question": "How did you hear about us?", "answer": "WorkIt", "ai": True},
        {"question": "Graduation year", "answer": "2028", "ai": False},
        {"question": "Cover Letter", "answer": "Dear Acme, ...", "ai": True},
        {"question": "Resume", "answer": "Sam_Own_Resume.pdf", "ai": False},
    ]


class Calls(WorkIt):
    """WorkIt's own record_applied over calls kept in `seen`: the job already at `before`, and the PUT of what the
    form sent answered with `status`."""

    def __init__(self, before, status=204):
        self._before, self._status, self.seen = before, status, []

    def add_by_link(self, url, company, title):
        return "job-8", self._before

    def applicant_id(self):
        return "me"

    def call(self, method, path, body=None, timeout=0):
        self.seen.append((method, path))
        if self._status != 204:
            raise WorkItError("refused", self._status)


def test_a_retried_applied_write_still_keeps_what_the_form_sent():
    """Fault: WorkIt took a write's stage, the connection dropped before its answers, and the write sent again stopped
    at "already applied" with the answers lost; or WorkIt's 409 for answers it has already failed the write."""
    answers = [{"question": "Why Acme?", "answer": "Trains.", "ai": True}]
    retried = Calls(Stage.APPLIED)

    assert retried.record_applied(POSTING.url, "Acme", "Intern", answers=answers) == Stage.APPLIED
    assert retried.seen == [("PUT", "/applicants/me/applications/job-8/sent")]
    assert Calls(Stage.APPLIED, 409).record_applied(POSTING.url, "Acme", "Intern", answers=answers) == Stage.APPLIED
    with pytest.raises(WorkItError):
        Calls(Stage.APPLIED, 422).record_applied(POSTING.url, "Acme", "Intern", answers=answers)


def test_a_cleanup_that_fails_never_makes_a_delivered_write_look_lost(tmp_path):
    """Fault: deleting the Mac's files after WorkIt took the write raised, so the write stayed queued to go again and
    the run said it was not in the Applications Tracker."""
    def busy(write):
        raise OSError("a file is busy")

    writes = WaitingWrites(Client(), tmp_path / "queue.json", delivered=busy)

    assert writes.send(Write("app-7", POSTING.url, "Acme", "Intern", Stage.APPLIED)) == \
        "in your Applications Tracker as Applied"
    assert writes.waiting() == []


class Down:
    """WorkIt that doesn't answer."""

    def applicant_id(self):
        raise Unreachable("api.workitjobs.ai: 503")

    def record_applied(self, *args, **kwargs):
        raise Unreachable("api.workitjobs.ai: 503")


def test_a_submit_still_on_its_way_to_workit_counts_as_applied(tmp_path):
    """Fault: with no Tracker file and no Record past a submit (W11), a submit WorkIt had not taken yet looked unsent,
    and the next run filled its form again for the student to send twice (Astranis, KAN-621)."""
    queue = tmp_path / "queue.json"
    WaitingWrites(Down(), queue).send(Write("app-7", POSTING.url, "Acme", "Intern", Stage.APPLIED))

    check = already_applied.Check(Down(), tmp_path / "tracker.json", (), queue)

    assert check.of(POSTING) is not None and check.problem()
    assert already_applied.Check(Down(), tmp_path / "tracker.json", (), tmp_path / "none.json").of(POSTING) is None


def test_the_apps_past_applications_come_from_its_applications_tracker_on_workit(tmp_path, monkeypatch):
    """Fault: with no Tracker file (W11), "Have you applied to Acme before?" lost the Yes WorkIt's Applications Tracker
    holds, and the student's other role at Acme went unseen."""
    monkeypatch.setattr(build, "STUDENT", True)
    monkeypatch.setattr(tracker, "ON_WORKIT", [])

    class Listed:
        def applicant_id(self):
            return "me"

        def applications(self, me):
            return [{"stage": "interviewing", "applied_at": "2026-11-02T15:00:00+00:00", "job": {
                "apply_url": "https://job-boards.greenhouse.io/acme/jobs/5", "company": "Acme", "title": "Data Intern"}}]

    assert already_applied.Check(Listed(), tmp_path / "tracker.json", (), tmp_path / "queue.json").problem() == ""

    assert tracker.past_applications(POSTING.url, tmp_path / "tracker.json") == (["Acme"], ["Acme"])
    assert [(o.title, o.applied) for o in other_roles.others(POSTING, [], tmp_path / "tracker.json")] == \
        [("Data Intern", True)]


def test_the_sent_resume_is_named_only_when_the_form_took_the_resume(monkeypatch):
    """Fault: a form with no resume field showed a resume under What You Sent, or a form that took the tailored
    resume named the profile's."""
    monkeypatch.setattr(student, "RESUME_REF", {"uploaded_resume_id": "u1"})
    took = [{"question": "Resume", "answer": "Sam_Resume.pdf", "ai": False}]
    tailored.GIVEN["app-7"] = {"built_resume_id": "b1"}

    assert student.resume_ref("app-7", [{"question": "Why Acme?", "answer": "Trains.", "ai": True}],
                              "Sam_Resume.pdf") == {}
    assert "app-7" not in tailored.GIVEN
    tailored.GIVEN["app-7"] = {"built_resume_id": "b1"}
    assert student.resume_ref("app-7", took, "Sam_Resume.pdf") == {"built_resume_id": "b1"}
    assert student.resume_ref("app-8", took, "Sam_Resume.pdf") == {"uploaded_resume_id": "u1"}


def test_a_page_can_hand_the_capture_only_this_forms_questions_and_never_a_password():
    """Fault: a page's own script called the capture's binding with names of its own and grew Apply's memory without
    end, or the capture read a password field into Apply's memory."""
    class Page:
        frames = []

        def expose_binding(self, name, take):
            self.take = take

    page, capture = Page(), sent_capture.Capture()
    capture.watch(page, [Question("why", "Why Acme?", "textarea"), Question("pw", "Create a password", "text")])

    page.take(None, json.dumps([["why", "Trains."], ["pw", "hunter2"], ["made-up", "x"]]))
    page.take(None, json.dumps([["why", "x"]] * 200_000))  # past MOST: dropped whole

    assert capture.values == {"why": "Trains."}


def test_an_application_with_no_company_loses_its_files_too(mac):
    """Fault: a Write with no company names tracker.UNKNOWN_COMPANY, whose folder names aren't its files', so a sent
    application's Record stayed on the Mac."""
    record = mac / "rehearsals/2026-11-27/company-app-5/form.png"
    record.parent.mkdir(parents=True)
    record.write_text("x")

    local_data.forget(tracker.UNKNOWN_COMPANY, "app-5")

    assert not record.exists()
