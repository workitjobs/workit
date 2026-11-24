"""The Student build (KAN-723, W3; D14): WorkIt Auto Apply holds no developer part, and nothing in it turns one on.
No browser: in CI.

- Its path (apply.student) loads no module in apply.build.DEVELOPER, so the compile can leave them all out.
- It reads no policies.yaml: `ask_model: claude` or `live_runs: true` in the data folder changes nothing.
- Where a Developer checkout would start `claude -p` (Claude fill, Rescue, Ask Claude, research), read Gmail or keep
  a Repair request, the Student build does none of it."""

import importlib.util
import json
import os
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from apply import (
    brief,
    build,
    code_box,
    fill_engine,
    orchestrator,
    profile,
    rehearsal,
    student,
    upload_origin,
)
from apply.adapters import ClaudeError, SetupError
from apply.answer_bank import AnswerBank
from apply.ask_model import live_claude
from apply.fillers import FILLERS
from apply.generic_fill import GenericFiller
from apply.model import FillError, Posting, Question, Status
from apply.profile import (
    load_policies as real_policies,  # before conftest's fixture strips the switches
)
from apply.worker import Result
from apply.workit import Unreachable

# In a new process, so nothing a test imported counts. It runs what the app runs first: its adapters, and a plain
# Worker's first page call (which loaded Ask Claude and Gmail, KAN-723). As conftest does, it blocks the network and
# gives keyring its null backend; APPLY_HOME is conftest's. It holds no model key, nor reads one: the app's calls go to
# WorkIt's Model route (ask_model: workit), and CI has no key.
LOADED = """import json, sys
from pathlib import Path
from apply import build
build.STUDENT = True
sys.path.insert(0, sys.argv[2])
import keyring, network_block
from keyring.backends import null
network_block.install()
network_block.begin()
keyring.set_keyring(null.Keyring())
from apply import student
from apply.answer_bank import AnswerBank
from apply.plain import fixed
from apply.profile import ApplicantProfile
run = student.adapters(ApplicantProfile.load(Path(sys.argv[1])), AnswerBank())
fixed.functions()
print(json.dumps({"loaded": sorted(m for m in sys.modules if m in build.DEVELOPER), "reached": network_block.end(),
                  "usage": type(run.usage.reading.__self__).__name__}))"""


@pytest.fixture
def student_build(monkeypatch):
    monkeypatch.setattr(build, "STUDENT", True)


def test_the_student_path_loads_no_developer_module(tmp_path):
    """Nuitka compiles what apply.student imports and leaves out each DEVELOPER module: one that the Student path
    imports, or loads as it runs, would fail in the app."""
    (tmp_path / "applicant-profile.yaml").write_text("identity: {}\n")
    run = subprocess.run([sys.executable, "-c", LOADED, str(tmp_path / "applicant-profile.yaml"), str(Path(__file__).parent)],
                         capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    loaded = json.loads(run.stdout)
    assert loaded.pop("usage") == "WorkItAsk"  # the run pauses at WorkIt's Usage cap, never past it
    assert loaded == {"loaded": [], "reached": []}, (
        "the Student build's path loads a developer module (apply.build.DEVELOPER), or reached the network: import it "
        "inside the function the Student build never reaches")


def test_every_developer_module_is_a_module():
    for name in build.DEVELOPER:  # a misspelt name would leave the real module in the compile
        assert importlib.util.find_spec(name) is not None, name


def test_policies_in_the_data_folder_change_nothing(tmp_path, monkeypatch, student_build):
    monkeypatch.setattr(profile, "load_policies", real_policies)
    mine, applicant = tmp_path / "policies.yaml", tmp_path / "applicant-profile.yaml"
    monkeypatch.setattr(profile, "OVERRIDE", mine)  # the data folder's, and the one beside the profile
    applicant.write_text("identity: {}\n")
    policies = lambda: (profile.load_policies(), profile.ApplicantProfile.load(applicant).policies())
    before = policies()
    mine.write_text("ask_model: claude\nlive_runs: true\nrepair: {max_per_day: 5}\nphone_push: true\n")
    assert policies() == before
    assert before[0]["ask_model"] == build.STUDENT_POLICIES["ask_model"]
    monkeypatch.setattr(build, "STUDENT", False)  # the same file does reach a Developer checkout
    assert profile.load_policies()["ask_model"] == "claude"
    assert profile.ApplicantProfile.load(applicant).policies()["live_runs"] is True


def test_even_ask_model_claude_builds_no_claude_cli():
    assert isinstance(live_claude({"ask_model": "claude"}, student.NoClaude()), student.NoClaude)


@pytest.mark.parametrize("call", ["ask", "drive", "research"])
def test_no_claude_refuses_every_call_to_claude(call):
    with pytest.raises(ClaudeError, match="WorkIt Auto Apply doesn't"):
        getattr(student.NoClaude(), call)(model="haiku")


class Filler:
    def __init__(self, accounts, rescue, **options):
        self.rescue = rescue


def posting(url: str) -> Posting:
    return Posting(id="p1", company="Acme", title="Intern", url=url)


def by_filler(url: str):
    """The Filler by_filler hands the form to, or the Result it gives without one."""
    given = []
    profile_ = SimpleNamespace(policy=lambda name: None, get=lambda key: None)
    result = orchestrator.by_filler(posting(url), SimpleNamespace(), profile_, student.NoClaude(),
                                    lambda: SimpleNamespace(), lambda filler, site: given.append(filler) or Result(Status.HELD))
    return given[0] if given else result


def test_a_job_system_with_no_filler_gets_the_generic_filler_not_claude_fill(student_build):
    """KAN-861 (W2 step 2): code reads and fills its form, a model only picks, through WorkIt's kinds; it never
    submits. Fault: Claude fill (a model driving the page) or a Filler that can press Submit."""
    filler = by_filler("https://careers.example.com/jobs/1")
    assert isinstance(filler, GenericFiller)
    with pytest.raises(SetupError, match="never presses Submit"):
        filler.submit(SimpleNamespace())


@pytest.fixture
def code_field(monkeypatch):
    """The held page's code-like boxes (apply.code_box): the form's own zip box; `came()` adds a code field."""
    shown = [("0|zip", "box")]
    monkeypatch.setattr(code_box, "boxes", lambda page: list(shown))
    monkeypatch.setattr(code_box, "new_boxes", lambda page, form: [b for b in shown if b[0] not in form])
    return SimpleNamespace(came=lambda: shown.append(("0|code", "box")))


def test_the_student_types_an_emailed_code_into_the_form_in_the_app(student_build, code_field):
    """KAN-855 (D9): no mail is read. Once a code field comes after the student's Submit, Needs you says so, once."""
    told = []
    watch = rehearsal._email_code(SimpleNamespace(), "greenhouse", lambda status, why: told.append((status, why)))
    watch.tick(None)
    code_field.came()
    watch.tick(None)
    assert told == []  # a code field with no press of the student's before it is the form's
    watch.pressed("Submit")
    watch.tick(None)
    watch.tick(None)
    assert told == [("needs code", rehearsal.TYPE_THE_CODE)]
    assert "press Fix here and type it" in rehearsal.TYPE_THE_CODE


def test_a_developer_checkouts_emailed_code_finds_its_field_through_code_box(code_field):
    """email_code.EmailCode reads the field from apply.code_box too. Its tick once named a local `boxes`, which hid
    the function and failed every held page's first turn (KAN-855): no browser here, so CI sees it."""
    told = []
    watch = rehearsal._email_code(SimpleNamespace(mailbox=SimpleNamespace(unavailable=lambda: "no Gmail here."),
                                                  clock=SimpleNamespace(now=lambda: datetime(2026, 11, 15))),
                                  "greenhouse", lambda status, why: told.append(status))
    watch.tick(None)
    watch.pressed("Submit")
    code_field.came()
    watch.tick(None)
    assert told == ["needs code"]


class Frame:
    def __init__(self, url: str, shows: str | None):
        self.url, self.shows = url, shows


def held(url: str, q: Question) -> SimpleNamespace:
    return SimpleNamespace(posting=posting(url), questions=(q,), where={})


def test_an_answer_from_the_app_goes_in_by_the_fill_engine_only_on_the_forms_own_site(monkeypatch):
    """KAN-855: no Rescue. The Fill engine fills the one field, in the frame that shows it. A captcha's frame never
    gets Apply's code, and another site's frame (a hostile page can hold one) never gets the answer (KAN-795's rule,
    upload_origin.frame_may_upload: here the form's own site is acme.example and Greenhouse's embedded form)."""
    q, tried = Question("q1", "Pronouns", "text"), []

    def fill(frame, site, questions, answers):
        tried.append(frame.url)
        if frame.shows is None:
            raise FillError("Pronouns: not in this frame")
        return {q.name: frame.shows}
    monkeypatch.setattr(fill_engine, "fill", fill)
    own = ("https://acme.example/", "https://boards.greenhouse.io/embed/")
    monkeypatch.setattr(upload_origin, "frame_may_upload", lambda frame: frame.url.startswith(own))
    page = SimpleNamespace(main_frame=Frame("https://acme.example/apply", None))
    page.frames = [page.main_frame, Frame("https://www.google.com/recaptcha/api2/anchor", "he/him"),
                   Frame("https://evil.example/frame", "he/him"), Frame("https://boards.greenhouse.io/embed/job_app", "he/him")]
    form = held("https://job-boards.greenhouse.io/acme/jobs/1", q)
    assert rehearsal._engine_fill(page, form, "Pronouns", "he/him")
    assert tried == ["https://acme.example/apply", "https://boards.greenhouse.io/embed/job_app"]
    assert not rehearsal._engine_fill(page, form, "Pronouns", "she/her")  # the field shows another answer
    assert not rehearsal._engine_fill(page, form, "Not on this form", "x")
    unknown = held("https://acme.taleo.net/careersection/2/jobdetail.ftl?job=1", q)
    assert not rehearsal._engine_fill(page, unknown, "Pronouns", "he/him")  # a job system the engine doesn't know


def test_a_field_the_form_didnt_take_starts_its_needs_you_box_with_the_planned_answer():
    planned = rehearsal._planned((("Pronouns", "he/him"), ("Languages", ["English", "Sinhala"]),
                                  ("Transcript", Path("/tmp/transcript.pdf"))))
    assert planned == {"Pronouns": "he/him", "Languages": "English; Sinhala"}  # a file: the window's file box


def test_a_filler_gets_no_rescue(student_build, monkeypatch):
    monkeypatch.setitem(FILLERS, "workday", Filler)
    assert by_filler("https://acme.wd1.myworkdayjobs.com/careers/job/1").rescue is None
    monkeypatch.setattr(build, "STUDENT", False)  # a Developer checkout's Filler has one
    assert by_filler("https://acme.wd1.myworkdayjobs.com/careers/job/1").rescue is not None


def test_no_gmail_no_ask_claude_no_repair_request(student_build):
    assert isinstance(rehearsal._email_code(SimpleNamespace(), "greenhouse", lambda status, why: None), code_box.TypeTheCode)
    board = SimpleNamespace(updates=[], update=lambda n, **fields: board.updates.append(fields),
                            asks=lambda n: [{"id": "1", "message": "fix the email field"}])
    asker = rehearsal._Ask(lambda: None, SimpleNamespace(board=board), None, 0, print)
    asker.open(SimpleNamespace())
    assert board.updates == [] and asker.asked() == []  # its tile takes no message, and none reaches Claude
    never = SimpleNamespace(add=lambda request: pytest.fail("the Student build kept a Repair request"))
    orchestrator.keep_repair_requests(SimpleNamespace(repairs=never), posting("https://x.example/1"), Result(Status.FAILED))


def test_a_brief_is_never_researched(student_build, tmp_path, monkeypatch):
    monkeypatch.setattr(brief, "BRIEFS", tmp_path)
    monkeypatch.setattr(brief, "research", lambda *a, **k: pytest.fail("the Student build researched a company"))
    claude = SimpleNamespace(ask_kind=lambda kind, data: {"team": ""})  # brief.team, a WorkIt kind (D5)
    assert brief.brief(posting("https://x.example/1"), SimpleNamespace(), claude, date(2026, 11, 14)) == ""


def test_the_student_builds_data_folder_is_the_systems_own_place():
    """Fault: WorkIt Auto Apply keeping a student's data in a Developer checkout's ~/.config/apply (D25). HOME is
    read once at import, so a new process with STUDENT set, and no APPLY_HOME, shows it."""
    environment = {k: v for k, v in os.environ.items() if k != "APPLY_HOME"}
    shown = subprocess.run([sys.executable, "-c", "from apply import build; build.STUDENT = True\n"
                            "from apply import home; print(home.HOME == home.APP_FOLDER)"],
                           capture_output=True, text=True, env=environment, check=True).stdout.strip()
    assert shown == "True"


def test_a_stopped_run_ends_only_once_its_workers_profiles_are_free(monkeypatch):
    """KAN-874. Fault: Stop takes the window back to the queue while a stopped fill's Chrome still holds its Worker
    profile, so a Start right after it fails with "worker-1 open in another browser"."""
    from apply.browsers import ProfileInUse

    class Site:
        busy = 3  # the stopped fill's Chrome quits after three looks

        def endpoint(self, worker):
            return None

        def close(self):
            pass

        def refuse_in_use(self):
            if self.busy:
                self.busy -= 1
                raise ProfileInUse("worker-1 open in another browser")

    site = Site()
    made = SimpleNamespace(site=site, answer_bank=None, keychain=None, everyday=None,
                           tracker=SimpleNamespace(rows=list, employer_accounts=list))
    monkeypatch.setattr(student, "FREE_POLL", 0.0)
    monkeypatch.setattr(student, "workers", lambda: 1)
    runs = student.Runs({}, AnswerBank(), make=lambda profile, bank: made, rehearse=lambda *args: None)

    runs.run(["https://jobs.lever.co/acme/1"], lambda board: None)

    assert site.busy == 0


def test_the_student_builds_tracker_outlives_a_launch_and_writes_workit(student_build):
    """Fault: the Student build's Tracker in memory, so its Employer accounts (and the passwords Remove All My Data
    removes) were lost at each launch, and the student's own Submit never reached their Applications Tracker."""
    from apply.home import HOME
    from apply.tracker import EmployerAccount, WorkItTracker

    applicant = profile.ApplicantProfile.load(HOME / "applicant-profile.yaml")
    account = EmployerAccount("Acme", "acme.wd1.myworkdayjobs.com", "test.person@example.com", date(2026, 11, 15))
    first = student.adapters(applicant, AnswerBank())
    assert isinstance(first.tracker, WorkItTracker)
    first.tracker.add_employer_account(account)
    assert student.adapters(applicant, AnswerBank()).tracker.employer_accounts() == [account]  # the next launch's


def test_a_run_waits_for_the_answer_bank_and_starts_nothing_without_it(monkeypatch):
    """With no bank yet, a run would draft every one-off question again and send none of them (W11)."""
    class Down:
        def read(self):
            raise Unreachable("WorkIt didn't answer")

    monkeypatch.setattr(student, "BANK_WAIT", 0.01)
    started = []
    runs = student.Runs({}, AnswerBank(Down()), make=lambda profile, bank: started.append("made"),
                        rehearse=lambda *args: started.append("rehearsed"))

    with pytest.raises(SetupError, match="Answer bank"):
        runs.run(["https://jobs.lever.co/acme/1"], show=lambda board: None)
    assert started == []


def test_the_compiled_apps_workers_start_its_own_program_as_the_relay():
    """Fault: a plain Worker's wrapper in the compiled app runs `-I host.py`, which the app has neither of (no Python,
    no .py file), or names its program by sys.executable, which in a Nuitka program is a `python` beside it that
    doesn't exist. Either way Chrome never reaches Apply and no plain Worker says hello (W8). Its own program, as the
    OS names it, is the relay when host.APP_FLAG comes first (scripts/app_entry.py); a checkout keeps its isolated
    Python on host.py."""
    import shlex

    import psutil

    from apply.plain import host, launcher

    assert shlex.split(launcher.host_command(compiled=True)) == [psutil.Process().exe(), host.APP_FLAG]
    assert shlex.split(launcher.host_command(compiled=False)) == [sys.executable, "-I", host.__file__]


def test_the_compiled_app_films_with_the_helper_it_ships_and_builds_none(tmp_path, monkeypatch):
    """Fault: the compiled app builds the window capture helper with swiftc, which a student's Mac lacks, so every
    plain Worker's tile drops to the slow captureVisibleTab path; or it films with a helper left in a cache folder
    instead of the one signed with the app (W8)."""
    from apply.plain import window_capture

    shipped = tmp_path / window_capture.BUNDLED_NAME
    shipped.write_bytes(b"helper")
    monkeypatch.setattr(window_capture, "BUNDLED", shipped)
    monkeypatch.setattr(window_capture.shutil, "which", lambda name: pytest.fail(f"looked for {name}"))
    window_capture.helper.cache_clear()
    try:
        assert window_capture.helper() == shipped
        shipped.unlink()
        window_capture.helper.cache_clear()
        assert window_capture.helper() is None  # a missing helper: the tile's extension frames, never a build
    finally:
        window_capture.helper.cache_clear()
