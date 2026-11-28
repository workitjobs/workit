"""Seam 1 for rehearsals: whole `rehearse` runs over pasted links, with fakes
for every outside system. Each link goes the real Application path to the
form's last page and stops there; no Filler's submit is ever called and no
job system records a Submission."""

import _thread
import json
import threading
import time
from collections.abc import Callable
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import pytest
import yaml
from conftest import (
    ANDURIL_URL,
    ARC_FORM,
    ARC_URL,
    HERMEUS_FORM,
    HERMEUS_URL,
    IMMUTA_FORM,
    IMMUTA_URL,
    PURE_STORAGE_FORM,
    PURE_STORAGE_URL,
    SKYDIO_FORM,
    SKYDIO_URL,
)
from fake_bamboohr import FakeBambooServer
from fake_bank import Source
from fake_jobvite import URL as JOBVITE_URL
from fake_jobvite import FakeJobviteServer
from fake_lever import FakeLeverServer
from fake_paylocity import URL as PAYLOCITY_URL
from fake_paylocity import FakePaylocityServer
from fake_rippling import FakeRipplingServer
from fake_workday import EXPERIENCE_STEPS, STEPS, FakeWorkdayServer
from fake_workday import Field as WorkdayField
from fakes import (
    FakeClaude,
    FakeClock,
    FakeJobServer,
    FakeMailbox,
    RecordingBoard,
    ScriptedUsage,
)
from playwright.sync_api import sync_playwright
from test_claude_fill import (
    ANSWERED,
    ESSAY,
    LUNAR_FORM,
    LUNAR_URL,
    WHY_LUNAR,
    BambooDriver,
    CaptchaDriver,
    JobviteDriver,
    PaylocityDriver,
    SendingDriver,
    captcha_profile,
)
from test_employer_accounts import CACI, CACI_FORM, CACI_URL, XCEL_FORM, XCEL_URL, World
from test_greenhouse_filler import board_listing_schools
from test_rippling_filler import RIPPLING_FORM, RIPPLING_URL
from test_run_answers import profile_with

from apply import auto_submit, batch, essays, rehearsal, rescue, send_button, worker
from apply.adapters import Adapters, ClaudeError, Drive, SetupError, UsageReading
from apply.answer_bank import AnswerBank
from apply.ashby import AshbyFiller
from apply.claude_fill import THANKS as FILL_THANKS
from apply.claude_fill import ClaudeFill
from apply.feed import SimplifyFeed
from apply.fillers import FILLERS
from apply.greenhouse import GreenhouseFiller
from apply.keychain import InMemoryKeychain
from apply.lever import LeverFiller
from apply.model import Posting
from apply.notify import RecordingNotifier
from apply.profile import ApplicantProfile
from apply.records import FolderRecords
from apply.repair import RepairRequests
from apply.tracker import InMemoryTracker
from apply.workday import WorkdayFiller

NOW = datetime(2026, 10, 15, 9, 30)


class NeverSubmits:
    """A real Filler whose submit fails the test."""

    def __init__(self, filler):
        self._filler = filler
        self.submitted = False

    def question_set(self, url, site):
        return self._filler.question_set(url, site)

    def fill(self, page, questions, answers):
        return self._filler.fill(page, questions, answers)

    def submit(self, page):
        self.submitted = True
        pytest.fail("a rehearsal called the Filler's submit")


def adapters(site, claude=None, **more) -> Adapters:
    more = {"tracker": InMemoryTracker(), "mailbox": FakeMailbox(), "usage": ScriptedUsage(), "clock": FakeClock(NOW),
            **more}
    return Adapters(feed=SimplifyFeed(lambda: b"[]"), site=site, claude=claude or FakeClaude(), **more)


def rehearse(urls, site, profile, claude=None, workers=1, **more) -> list[rehearsal.Rehearsed]:
    lines = []
    done = rehearsal.rehearse(urls, adapters(site, claude, **more), ApplicantProfile.load(profile), workers,
                              keep_open=False, out=lines.append)
    assert len(lines) == len(urls)  # one summary line per link
    return done


SCRIPTED = {
    "greenhouse": (lambda: FakeJobServer(ARC_FORM), ARC_URL, GreenhouseFiller),
    "ashby": (lambda: FakeJobServer(SKYDIO_FORM), SKYDIO_URL, AshbyFiller),
    "lever": (lambda: FakeLeverServer(IMMUTA_FORM, parse_delay=0.2), IMMUTA_URL, LeverFiller),
}
# The company and role each job system names for its Posting.
NAMED = {
    "greenhouse": ("Arc Boat Company", "Software Engineering Intern"),
    "ashby": ("Skydio", "Software Engineer Intern - Summer 2027"),
    "lever": ("Immuta", "Full-Stack Engineering Internship - Summer 2027"),
}


@pytest.mark.parametrize("system", SCRIPTED)
def test_a_rehearsal_fills_the_form_to_its_last_page_and_never_submits(monkeypatch, tmp_path, system):
    server, url, filler_class = SCRIPTED[system]
    filler = NeverSubmits(filler_class())
    monkeypatch.setitem(FILLERS, system, filler)

    with server() as fake:
        [done] = rehearse([url], fake, profile_with(tmp_path))

    assert (done.posting.url, done.posting.job_system) == (url, system)
    assert (done.posting.company, done.posting.title) == NAMED[system]
    assert done.line().startswith(" | ".join([*NAMED[system], system]))
    assert done.outcome == "ready to submit", done.why
    assert done.filled > 0
    assert not filler.submitted
    assert fake.submissions == []
    line = done.line()
    assert system in line and "ready to submit" in line and f"{done.filled}/{done.asked} fields filled" in line


def test_at_a_usage_limit_no_form_opens_until_it_resets(monkeypatch, tmp_path):
    # The Student build's limit is WorkIt's Usage cap (ask_model.WorkItAsk.reading). Opened at it, each form was
    # refused at its first ask and ended paused, never started again.
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    reset = datetime(2026, 10, 16, 0, 0)
    opened_while_paused, board = [], RecordingBoard()
    with FakeJobServer(ARC_FORM) as fake:
        clock = FakeClock(NOW, on_sleep=lambda: opened_while_paused.append(list(fake.workers)))
        usage = ScriptedUsage(lambda: UsageReading(limited=True, resets_at=reset) if clock.now() < reset
                              else UsageReading())
        [done] = rehearse([ARC_URL], fake, profile_with(tmp_path), usage=usage, clock=clock, board=board)

    assert opened_while_paused == [[]] and clock.slept == [reset]
    assert done.outcome == "ready to submit", done.why
    paused = board.runs.index({"paused_until": reset.isoformat(timespec="minutes")})
    assert board.runs[paused + 1] == {"paused_until": None}


@pytest.mark.parametrize("error", [ClaudeError("claude -p failed: overloaded"),  # its probe refused
                                   SetupError("Claude isn't logged in")])  # ask_model: claude, logged out
def test_a_usage_reading_that_fails_never_stops_the_link(monkeypatch, tmp_path, error):
    # Fault: the reading's error reaching the link. Read before the link's try, it ended the link's thread holding
    # its Worker's turn, and the run waited on its summary until Ctrl-C; the form's own calls say what is wrong.
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))

    def fails() -> UsageReading:
        raise error

    ended = []
    with FakeJobServer(ARC_FORM) as fake:
        run = threading.Thread(target=lambda: ended.extend(
            rehearse([ARC_URL], fake, profile_with(tmp_path), usage=ScriptedUsage(fails))), daemon=True)
        run.start()
        run.join(60)  # a fill here takes about 2 s

    assert not run.is_alive(), "the run waited on the link's summary"
    [done] = ended
    assert done.outcome == "ready to submit", done.why


def test_missing_facts_leave_their_fields_blank_and_are_listed(monkeypatch, tmp_path):
    filler = NeverSubmits(GreenhouseFiller())
    monkeypatch.setitem(FILLERS, "greenhouse", filler)
    profile = profile_with(tmp_path, **{"identity.email": None, "identity.legal_last_name": None})

    with FakeJobServer(ARC_FORM) as fake:
        [done] = rehearse([ARC_URL], fake, profile)

    assert done.outcome == "ready to submit", done.why
    assert done.missing == ("Last Name", "Email")
    assert done.filled >= 6  # first name, phone, résumé, work authorization...: every answer it had
    assert "Missing facts: Last Name; Email" in done.line()
    assert not filler.submitted and fake.submissions == []


def test_holds_do_not_stop_a_rehearsal_and_claude_fill_never_clicks_submit(monkeypatch, tmp_path):
    monkeypatch.setattr(ClaudeFill, "submit", lambda self, page: pytest.fail("a rehearsal clicked Claude fill's submit"))
    # No start date in the profile, so "Date Available" is a Missing fact.
    profile = profile_with(tmp_path, **{f"answered_questions.{q}": a for q, a in ANSWERED.items() if q != "Date Available"},
                           **{"logistics.earliest_start_date": None})
    (tmp_path / "policies.yaml").write_text("calibration_run: 10\n")  # a run would hold its first 10
    claude = FakeClaude(driver=BambooDriver(), essays={"Tell us why": WHY_LUNAR},
                        drive_tokens=[18_000, 31_500], ask_tokens=1_000)

    with FakeBambooServer(LUNAR_FORM) as server:
        [done] = rehearse([LUNAR_URL], server, profile, claude)

    assert (done.posting.job_system, done.outcome) == ("other", "ready to submit")
    # Its High-stakes essay was written and filled anyway; a run would hold it for that, and for the Calibration run.
    assert any(asked["kind"] == "essays.write" for asked in claude.kinds)
    assert f"High-stakes essay: '{ESSAY}'" in done.why
    assert "Calibration run: Application 1 of 10" in done.why
    assert done.missing == ("Date Available",)
    # Two drives, then 1,000 for each other call: the essay's probe, plan, draft, checks and editor's passes, and the review.
    assert done.tokens == 18_000 + 31_500 + 1_000 * (len(claude.calls) + len(claude.kinds) - 2)  # kinds spend too
    assert "Claude fill:" not in done.why  # its cost is in the tokens, not among the holds


def test_hold_high_stakes_essays_false_holds_no_essay_only_for_review(tmp_path):
    """Fault: full_auto's hold_high_stakes_essays: false ignored, so every Ashby-like essay still waits for review."""
    profile = profile_with(tmp_path, **{f"answered_questions.{q}": a for q, a in ANSWERED.items()})
    (tmp_path / "policies.yaml").write_text("hold_high_stakes_essays: false\ncalibration_run: 0\n")
    claude = FakeClaude(driver=BambooDriver(), essays={"Tell us why": WHY_LUNAR})

    with FakeBambooServer(LUNAR_FORM) as server:
        [done] = rehearse([LUNAR_URL], server, profile, claude)

    assert any(asked["kind"] == "essays.write" for asked in claude.kinds)
    assert "High-stakes essay" not in done.why
    assert server.submissions == []


@pytest.mark.parametrize(("names", "outcome"), [("Submit Application", "ready to submit"), ("", "handoff")])
def test_claude_clicking_the_forms_submit_in_a_rehearsal_sends_nothing(monkeypatch, tmp_path, names, outcome):
    # Roblox (live): a click on the submit Claude then names leaves the form filled, not sent; any other is a Handoff.
    monkeypatch.setattr(ClaudeFill, "submit", lambda self, page: pytest.fail("a rehearsal clicked Claude fill's submit"))
    profile = profile_with(tmp_path, **{f"answered_questions.{q}": a for q, a in ANSWERED.items()},
                           **{f"answered_questions.{ESSAY}": "Lunar rovers are what I build in my spare time."})

    with FakeBambooServer(LUNAR_FORM) as server:
        [done] = rehearse([LUNAR_URL], server, profile, FakeClaude(driver=SendingDriver(names=names)))

    assert done.outcome == outcome
    if names == "":
        assert 'Apply blocked the "Submit Application" click while Claude filled the form' in done.why
    assert server.submissions == []


def test_each_filled_rehearsal_keeps_its_record_in_a_local_folder(tmp_path):
    profile = profile_with(tmp_path, **{f"answered_questions.{q}": a for q, a in ANSWERED.items()})
    claude = FakeClaude(driver=BambooDriver(), essays={"Tell us why": "I build lunar rover software."},
                        reviews=[["Phone: the number is in the Email field"]])
    records = FolderRecords(tmp_path / "rehearsals")

    with FakeBambooServer(LUNAR_FORM) as server:
        [done] = rehearse([LUNAR_URL], server, profile, claude, records=records)

    folder = tmp_path / "rehearsals" / "2026-10-15" / f"lunar-outpost-{done.posting.id}"  # named by its page
    assert done.record == str(folder)
    readme = (folder / "README.md").read_text()
    assert "Rehearsal, not submitted. Pre-submit check: failed." in readme
    assert "Pre-submit review: Phone: the number is in the Email field" in readme
    essays_md = (folder / "essays.md").read_text()
    assert essays_md.startswith(f"## {ESSAY}\nPlan: why-company | ")
    assert "## Additional Comments?" not in essays_md  # an optional catch-all box stays blank (KAN-625)
    essay = essays_md.splitlines()[-1]  # the candidate the writer picked
    assert essay in (folder / "answers.json").read_text()
    assert (folder / "form.png").read_bytes().startswith(b"\x89PNG")
    assert server.submissions == []


class RefusedOnce(FakeClaude):
    """Opus's safeguards refused the essay write, and Sonnet answered it (claude_cli.ClaudeCLI.refused)."""

    def __init__(self, **given):
        super().__init__(**given)
        self._refused = threading.local()

    def refused(self) -> list[str]:
        return list(getattr(self._refused, "kinds", ()))

    def ask_kind(self, kind: str, data: dict) -> dict:
        if kind == "essays.write":
            self._refused.kinds = [*self.refused(), kind]
        return super().ask_kind(kind, data)


def test_a_call_opus_refused_and_sonnet_answered_is_said_in_the_fills_record(tmp_path):
    """Fault: Mach Industries' (run11) refusal, once Sonnet answers it, leaving no word of it in the Record."""
    claude = RefusedOnce(driver=BambooDriver(), essays={"Tell us why": "I build lunar rover software."})
    records = FolderRecords(tmp_path / "rehearsals")

    with FakeBambooServer(LUNAR_FORM) as server:
        [done] = rehearse([LUNAR_URL], server, profile_with(tmp_path), claude, records=records)

    said = "Opus's safeguards refused essays.write, so Sonnet answered it"
    assert [line.split(" ", 1)[1] for line in done.history] == [said]
    assert said in (Path(done.record) / "README.md").read_text()


# A pasted link on a job system with no Filler names neither company nor role:
# the form's own page does, by its title (Jobvite's and Paylocity's, live).
PAGE_NAMED = {
    "jobvite": (FakeJobviteServer, JOBVITE_URL, JobviteDriver,
                "# Tyler Technologies: Software Development Intern, Summer 2027"),
    "paylocity": (FakePaylocityServer, PAYLOCITY_URL, PaylocityDriver,
                  "# North Atlantic Industries, Inc: Intern - Full Stack Software Engineer (Summer 2027)"),
}


@pytest.mark.parametrize("system", PAGE_NAMED)
def test_a_claude_fill_record_is_headed_with_the_company_and_role_its_page_names(tmp_path, system):
    server, url, driver, heading = PAGE_NAMED[system]

    with server() as site:
        [done] = rehearse([url], site, profile_with(tmp_path), FakeClaude(driver=driver()),
                          records=FolderRecords(tmp_path / "rehearsals"))

    assert (Path(done.record) / "README.md").read_text().splitlines()[0] == heading


GOOGLE = {"workday_sign_in": "google"}  # policies.yaml: Sign in with Google where the tenant offers it


class NeverSubmittingWorkday(WorkdayFiller):
    def submit(self, page):
        pytest.fail("a rehearsal called the Workday Filler's submit")


def test_a_workday_rehearsal_whose_create_account_goes_back_to_sign_in_resets_nothing_and_says_so(monkeypatch):
    # ASML (live, 2026-11-03): Workday showed Sign In with no error, and Lisul had an account there already.
    monkeypatch.setitem(FILLERS, "workday", NeverSubmittingWorkday)
    world = World()

    with FakeWorkdayServer(CACI_FORM, keychain=world.keychain, mailbox=world.mailbox, exists_quietly=True,
                           accounts={(CACI, "test.person@example.com"): "Made-By-Hand1!"}) as server:
        [done] = rehearse([CACI_URL], server, world.profile, keychain=world.keychain, mailbox=world.mailbox)

    assert "may already have an account for your email: reset its password once, or save it with " \
           f"uv run keyring set apply-ats {CACI}" in done.why, done.why
    assert server.resets == [] and world.keychain.password(CACI) is None


def test_a_workday_rehearsal_whose_create_account_goes_to_the_bare_sign_in_view_signs_in_and_stops_unsent(monkeypatch):
    # Visa's tenant (live, 2026-11-03): Workday made the account, then loaded its bare Sign In view.
    monkeypatch.setitem(FILLERS, "workday", NeverSubmittingWorkday)
    world = World()

    with FakeWorkdayServer(CACI_FORM, keychain=world.keychain, mailbox=world.mailbox, to_sign_in=True) as server:
        [done] = rehearse([CACI_URL], server, world.profile, keychain=world.keychain, mailbox=world.mailbox)

    assert done.outcome == "ready to submit", done.why
    [made] = server.created
    assert world.keychain.password(CACI) == made["password"]
    assert server.sign_ins == [(CACI, "test.person@example.com", True)] and server.submissions == []


def test_a_workday_rehearsal_makes_an_employer_account_reads_its_link_from_gmail_and_stops_unsent(monkeypatch):
    monkeypatch.setitem(FILLERS, "workday", NeverSubmittingWorkday)
    world, tracker = World(), InMemoryTracker()

    with FakeWorkdayServer(CACI_FORM, keychain=world.keychain, mailbox=world.mailbox, verify_email=(CACI,)) as server:
        [done] = rehearse([CACI_URL], server, world.profile, keychain=world.keychain, mailbox=world.mailbox,
                          tracker=tracker)

    assert done.outcome == "ready to submit", done.why
    [made] = server.created
    assert made["keychain"] == made["password"] == world.keychain.password(CACI)  # saved before the form was sent
    assert server.account(CACI, "test.person@example.com")["verified"]
    assert [a.site for a in tracker.employer_accounts()] == [CACI]
    assert server.submissions == []


def test_a_live_rehearsals_new_employer_account_is_listed_in_the_kept_tracker(monkeypatch):
    # A live rehearsal's own Tracker is a throwaway (no rows for rehearsed links), but the account it
    # made is real: it is listed where Applications Lisul submits are kept, the Employer accounts list
    # that `apply accounts` and the WorkIt extension's Apply sign-in read (KAN-592).
    monkeypatch.setitem(FILLERS, "workday", NeverSubmittingWorkday)
    world, throwaway, kept = World(), InMemoryTracker(), InMemoryTracker()

    with FakeWorkdayServer(CACI_FORM, keychain=world.keychain, mailbox=world.mailbox, verify_email=(CACI,)) as server:
        rehearsal.rehearse([CACI_URL], adapters(server, None, keychain=world.keychain, mailbox=world.mailbox,
                                                 tracker=throwaway),
                           ApplicantProfile.load(world.profile), 1, keep_open=False, out=lambda line: None,
                           submitted_to=kept)

    assert [a.site for a in kept.employer_accounts()] == [CACI]
    assert throwaway.employer_accounts() == []


def test_a_workday_rehearsal_whose_link_gmail_cannot_read_needs_sign_in_saying_so(monkeypatch, tmp_path):
    monkeypatch.setitem(FILLERS, "workday", NeverSubmittingWorkday)
    keychain, mailbox = InMemoryKeychain(), FakeMailbox(set_up=False)

    with FakeWorkdayServer(CACI_FORM, keychain=keychain, mailbox=mailbox, verify_email=(CACI,)) as server:
        [done] = rehearse([CACI_URL], server, profile_with(tmp_path), keychain=keychain, mailbox=mailbox)

    assert done.outcome == "needs sign-in", done.why
    assert "Gmail isn't set up for Apply" in done.why and "verification email can't be read" in done.why
    assert "needs sign-in" in done.line()
    assert mailbox.looks == 0
    assert keychain.password(CACI) == server.account(CACI, "test.person@example.com")["password"]
    assert server.submissions == []


JOBS = [
    {"employer": "Acme Rail", "title": "Software Engineer Intern", "location": "Springfield, IL", "start": "2026-06", "end": "2026-08"},
    {"employer": "Cloud Co", "title": "Data Intern", "location": "Remote", "start": "2025-06", "end": "2025-08"},
]
SCHOOLING = {"school": "Stony Brook University", "degree": "Bachelor's Degree", "majors": ["Computer Science"],
             "gpa_cumulative": 3.77, "start_date": "2024-08", "expected_graduation": "2028-05"}


def experience_profile(**schooling) -> World:
    """A World whose profile answers every step, with jobs and a school (and `schooling`'s education facts)."""
    world = World()
    profile = yaml.safe_load(world.profile.read_text())
    profile["experience_facts"] = {"employment_history": JOBS}
    profile["education"] |= SCHOOLING | schooling
    world.profile.write_text(yaml.safe_dump(profile))
    return world


def test_a_workday_rehearsal_fills_my_experience_an_entry_per_job_and_school_to_review(monkeypatch, tmp_path):
    # Snap's My Experience requires Work Experience and Education entries (seen live).
    monkeypatch.setitem(FILLERS, "workday", NeverSubmittingWorkday)
    # Snap offers B.A. and B.S. for the profile's Bachelor's Degree: its degree type says which.
    # The tenant has no Computer Science (AmFam's, live): its search picks a wording Lisul accepts.
    world = experience_profile(degree_type="Bachelor of Science",
                               major_wordings={"Computer Science": ["Computer and Information Science"]})

    with FakeWorkdayServer(XCEL_FORM, steps=EXPERIENCE_STEPS) as server:
        [done] = rehearse([XCEL_URL], server, world.profile)

    assert done.outcome == "ready to submit", done.why
    assert done.missing == ()
    assert "Field of Study" not in done.why
    saved = server.saved("xcelenergy.wd1.myworkdayjobs.com")
    assert [(job["companyName"], job["jobTitle"], job["location"], job["startDate"], job["endDate"])
            for job in saved["workExperience"]] == [
        ("Acme Rail", "Software Engineer Intern", "Springfield, IL", "06/2026", "08/2026"),
        ("Cloud Co", "Data Intern", "Remote", "06/2025", "08/2025"),
    ]
    assert saved["education"] == [{"schoolName": "Stony Brook University", "degree": "B.S.",
                                   "fieldOfStudy": ["Computer and Information Science"], "gradeAverage": "3.77",
                                   "firstYearAttended": "2024", "lastYearAttended": "2028"}]
    assert saved["websites"] == [{"url": "https://test-person.example.com"}]  # the profile's portfolio
    assert server.submissions == []


# Arrowstreet Capital's Application Questions 1 of 2 (rehearsed 2026-11-04): an intro, the current school's questions, a
# bare From and the graduation, whose help text asks the first of the month. Claude answered From with the internship's
# start, and the Answer bank kept it as "from (mm/dd/yyyy)" for every form.
SCHOOL_INTRO = "When entering your education information below, please enter your current university information."
SCHOOL_QUESTIONS = ("Application Questions 1 of 2", [
    WorkdayField("school", "Current School/University", "text", True, intro=SCHOOL_INTRO),
    WorkdayField("degree", "Degree", "dropdown", True, ("Bachelors", "Masters")),
    WorkdayField("gpa", "Overall GPA", "text", True),
    WorkdayField("from", "From", "date", True, format="MM/DD/YYYY"),
    WorkdayField("graduation", "Please enter the first of the month and year that you are planning to graduate. "
                 "Anticipated Graduation", "date", True, format="MM/DD/YYYY"),
])


def _steps(step) -> list:
    return [*STEPS[:2], step, *STEPS[2:]]


def test_a_workday_rehearsal_answers_a_bare_from_for_its_school_and_banks_nothing_by_its_label(monkeypatch, tmp_path):
    monkeypatch.setitem(FILLERS, "workday", NeverSubmittingWorkday)
    world = experience_profile(graduation_day=21)
    bank, claude = AnswerBank(), FakeClaude(drafts={"From": "05/26/2027"})

    with FakeWorkdayServer(XCEL_FORM, steps=_steps(SCHOOL_QUESTIONS)) as server:
        [done] = rehearse([XCEL_URL], server, world.profile, claude, answer_bank=bank)

    assert done.outcome == "ready to submit", done.why
    saved = server.saved("xcelenergy.wd1.myworkdayjobs.com")
    # The school's start, not the internship's; the graduation on the first of its month, as its help text asks.
    assert (saved["from"], saved["graduation"]) == ("08/01/2024", "05/01/2028")
    assert not any(asked["data"]["short_questions"] for asked in claude.kinds if asked["kind"] == "essays.write")  # the plan answered it
    assert all("from" not in question.casefold() for question in bank.answers())
    assert server.submissions == []


def test_a_bare_from_claude_drafts_is_told_its_section_and_banked_only_under_it(monkeypatch, tmp_path):
    monkeypatch.setitem(FILLERS, "workday", NeverSubmittingWorkday)
    job = ("Application Questions 1 of 2", [WorkdayField("title", "Job Title", "text", True),
                                            WorkdayField("from", "From", "date", True, format="MM/DD/YYYY")])
    bank, claude = AnswerBank(), FakeClaude(drafts={"Job Title": "Intern", "From": "05/24/2027"})

    world = experience_profile()  # kept: its folder holds the profile
    with FakeWorkdayServer(XCEL_FORM, steps=_steps(job)) as server:
        [done] = rehearse([XCEL_URL], server, world.profile, claude, answer_bank=bank)

    assert done.outcome == "ready to submit", done.why
    [drafts] = [k["data"]["short_questions"] for k in claude.kinds if k["kind"] == "essays.write" and k["data"]["short_questions"]]
    asked = {d["label"]: d for d in drafts.values()}
    assert asked["From"]["about"] == "work experience" and not asked["Job Title"]["about"]
    assert [entry.question for entry in bank.entries()] == ["Job Title", "work experience / From (MM/DD/YYYY)"]
    assert server.submissions == []


def test_a_draft_names_the_workit_job_the_queue_gave_its_link(monkeypatch, tmp_path):
    """Fault: the draft named its company alone, which WorkIt's rule would have to trust (W11), not the job the
    student's Auto Apply queue gave the link."""
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))

    with FakeJobServer(ARC_FORM) as fake:
        [done] = rehearse([ARC_URL], fake, profile_with(tmp_path), jobs={ARC_URL: "j1"})

    assert done.outcome == "ready to submit", done.why
    assert done.posting.job_id == "j1"  # the Worker's drafts send it (test_claude_answers)
    assert fake.submissions == []


def test_a_rehearsal_reads_the_bank_again_when_the_usage_reading_names_a_newer_version(monkeypatch, tmp_path):
    """W11: the version rides on the usage reading each link already asks, so the bank costs no request of its own
    unless it changed."""
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    workit = Source()  # at version 7
    bank = AnswerBank(workit)
    bank.load()

    with FakeJobServer(ARC_FORM) as fake:
        rehearse([ARC_URL], fake, profile_with(tmp_path), answer_bank=bank,
                 usage=ScriptedUsage(lambda: UsageReading(bank_version=8)))

    assert (workit.reads, workit.asked) == (2, 0)


def test_the_pre_submit_reviews_fix_is_filled_before_the_form_shows_as_ready(monkeypatch, tmp_path):
    # A bare From nothing on the form places: Claude's draft is never banked, and when the review names the right
    # answer for a wrong one, that answer is filled and the form reviewed again, never left as a banner.
    monkeypatch.setitem(FILLERS, "workday", NeverSubmittingWorkday)
    bare = ("Application Questions 1 of 2", [WorkdayField("from", "From", "date", True, format="MM/DD/YYYY")])
    problem = "'From (MM/DD/YYYY)': 05/24/2027 is the internship start date, not his school start"
    bank = AnswerBank()
    claude = FakeClaude(drafts={"From": "05/24/2027"},  # a number the profile holds (its earliest start), so it is used
                        # A fix for an answer from the profile is never taken (General Motors' degree, live).
                        reviews=[{"problems": [problem, "First Name: not his name"],
                                  "fixes": [{"question": "From (MM/DD/YYYY)", "answer": "08/01/2024"},
                                            {"question": "First Name", "answer": "Someone"}]}])

    world = experience_profile()
    with FakeWorkdayServer(XCEL_FORM, steps=_steps(bare)) as server:
        [done] = rehearse([XCEL_URL], server, world.profile, claude, answer_bank=bank)

    assert done.outcome == "ready to submit", done.why
    assert "Pre-submit review" not in done.why
    saved = server.saved("xcelenergy.wd1.myworkdayjobs.com")
    assert saved["from"] == "08/01/2024" and saved["legalName--firstName"] != "Someone"
    [drafts] = [k["data"]["short_questions"] for k in claude.kinds if k["kind"] == "essays.write" and k["data"]["short_questions"]]
    assert [d["about"] for d in drafts.values()] == ["unknown"]
    assert sum(asked["kind"] == "presubmit.review" for asked in claude.kinds) == 2  # reviewed again after the fix
    assert bank.entries() == []
    assert server.submissions == []


AUTHORIZED = "Are you legally authorized to work in the United States?"


def test_the_reviews_fix_for_a_legal_answer_is_filled_over_the_profiles(monkeypatch, tmp_path):
    # Saronic's U.S. Person "No" came from the plan's own (wrong) rule, and the review's fix was left as a banner
    # (live, 2026-11-04). A legal or eligibility answer the review finds wrong is filled with its fix, then reviewed
    # again, though the plan took it from the profile. Another profile answer's fix is still never taken.
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    claude = FakeClaude(reviews=[{"problems": [f"{AUTHORIZED}: answered No, but the profile says he is authorized",
                                               "First Name: not his name"],
                                  "fixes": [{"question": AUTHORIZED, "answer": "Yes"},
                                            {"question": "First Name", "answer": "Someone"}]}])
    profile = profile_with(tmp_path, **{"work_authorization.authorized_to_work_us": False})
    records, board = FolderRecords(tmp_path / "rehearsals"), RecordingBoard()

    with FakeJobServer(ARC_FORM) as fake:
        [done] = rehearse([ARC_URL], fake, profile, claude, records=records, board=board)

    shown = {a["question"].strip(): a["on_page"] for a in json.loads((Path(done.record) / "answers.json").read_text())}
    assert shown[AUTHORIZED] == "Yes" and shown["First Name"] != "Someone"
    # The student page says what the review changed, from what to what, and that WorkIt wrote the new answer.
    assert board.captions[0]["fixed"] == [{"question": AUTHORIZED, "was": "No", "now": "Yes"}]
    assert {a["question"]: a["from"] for a in board.captions[0]["answers"]}[AUTHORIZED] == "written"
    assert sum(asked["kind"] == "presubmit.review" for asked in claude.kinds) == 2  # reviewed again after the fix
    assert done.legal == ()
    assert fake.submissions == []


TOO_MUCH = "Last Name: gives a middle name too, which the question doesn't ask for"
TWO_NAMES = {"identity.legal_last_name": "Quinn Person"}


def test_apply_fixes_a_review_problem_the_review_gave_no_fix_for_before_the_form_shows_as_ready(monkeypatch, tmp_path):
    # Abridge (live, 2026-11-26): the review held a profile answer as more than its question asks, with no fix, and
    # it reached Needs you. Apply asks for the fix, fills it, reads the form back and reviews it again: a fix that
    # only narrows the profile's answer states no new fact, so it goes in over it.
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    claude = FakeClaude(reviews=[[TOO_MUCH]], fixes=[{"fixes": [{"question": "Last Name", "answer": "Person"}], "yours": []}])
    records, board = FolderRecords(tmp_path / "rehearsals"), RecordingBoard()

    with FakeJobServer(ARC_FORM) as fake:
        [done] = rehearse([ARC_URL], fake, profile_with(tmp_path, **TWO_NAMES), claude, records=records, board=board)

    assert done.outcome == "ready to submit", done.why
    assert "Pre-submit review" not in done.why
    shown = {a["question"].strip(): a["on_page"] for a in json.loads((Path(done.record) / "answers.json").read_text())}
    assert shown["Last Name"] == "Person"
    assert board.captions[0]["fixed"] == [{"question": "Last Name", "was": "Quinn Person", "now": "Person"}]
    assert "## Fixed before submit" in (readme := (Path(done.record) / "README.md").read_text())  # the Record logs it
    assert "- Last Name: Quinn Person → Person" in readme
    [asked] = [k["data"] for k in claude.kinds if k["kind"] == "presubmit.fix"]
    assert asked["problems"] == [TOO_MUCH]
    assert [k["kind"] for k in claude.kinds].count("presubmit.review") == 2  # reviewed again after the fix
    assert fake.submissions == []


def test_a_self_fix_that_states_a_new_fact_is_never_filled_over_the_profiles(monkeypatch, tmp_path):
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    claude = FakeClaude(reviews=[["First Name: not his name"]],
                        fixes=[{"fixes": [{"question": "First Name", "answer": "Someone"}], "yours": []}])

    with FakeJobServer(ARC_FORM) as fake:
        [done] = rehearse([ARC_URL], fake, profile_with(tmp_path), claude)

    assert "Pre-submit review: First Name: not his name" in done.why
    assert [k["kind"] for k in claude.kinds].count("presubmit.review") == 1
    assert fake.submissions == []


def test_a_problem_still_there_after_two_self_fixes_reaches_the_student(monkeypatch, tmp_path):
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    narrower = [{"fixes": [{"question": "Last Name", "answer": answer}], "yours": []} for answer in ("Quinn Person", "Person")]
    claude = FakeClaude(reviews=[[TOO_MUCH]] * 3, fixes=narrower)

    with FakeJobServer(ARC_FORM) as fake:
        [done] = rehearse([ARC_URL], fake, profile_with(tmp_path, **{"identity.legal_last_name": "Ann Quinn Person"}), claude)

    assert f"Pre-submit review: {TOO_MUCH}" in done.why
    kinds = [k["kind"] for k in claude.kinds]
    assert (kinds.count("presubmit.fix"), kinds.count("presubmit.review")) == (2, 3)
    assert fake.submissions == []


def test_a_legal_problem_the_review_gives_no_fix_for_holds_submit_until_lisul_dismisses_it(monkeypatch, tmp_path):
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    problem = 'The U.S. Person status question is answered "No", but the profile says he is a U.S. citizen'
    claude = FakeClaude(reviews=[[problem, "Why Arc?: names no product"]])

    with FakeJobServer(ARC_FORM) as fake:
        [done] = rehearse([ARC_URL], fake, profile_with(tmp_path), claude)

    assert done.legal == (("", problem),)  # the essay's problem is a banner, not a hold
    assert done.holding() == problem
    done.dismiss_holds()  # the held note's Dismiss
    assert done.holding() == ""
    assert fake.submissions == []


def test_a_workday_rehearsal_stops_where_google_wants_more_than_an_account_pick(monkeypatch, tmp_path):
    monkeypatch.setitem(FILLERS, "workday", NeverSubmittingWorkday)

    with FakeWorkdayServer(XCEL_FORM, google="password") as server:
        [done] = rehearse([XCEL_URL], server, profile_with(tmp_path, GOOGLE), records=FolderRecords(tmp_path / "rehearsals"))

    assert done.outcome == "handoff" and "Google asked for more than an account pick" in done.why
    assert "Rehearsal, not submitted: handoff: Google asked" in (Path(done.record) / "README.md").read_text()  # its Record too
    assert server.submissions == []


def test_a_workday_rehearsal_stops_as_needs_sign_in_when_google_refuses_the_browser(monkeypatch, tmp_path):
    monkeypatch.setitem(FILLERS, "workday", NeverSubmittingWorkday)

    with FakeWorkdayServer(XCEL_FORM, google="rejected") as server:
        [done] = rehearse([XCEL_URL], server, profile_with(tmp_path, GOOGLE), records=FolderRecords(tmp_path / "rehearsals"))

    assert done.outcome == "needs sign-in" and done.why.startswith("Google refused Sign in with Google")
    assert server.submissions == []


class Watched:
    """A job site that counts its open pages, opened and closed on several threads."""

    def __init__(self, site):
        self._site = site
        self._lock = threading.Lock()
        self.open_now = 0

    def fetch(self, url, body=None):
        return self._site.fetch(url, body)

    @contextmanager
    def open(self, url, worker=0):
        with self._site.open(url, worker) as page:
            self._count(+1)
            try:
                yield page
            finally:
                self._count(-1)

    def _count(self, change: int) -> None:
        with self._lock:
            self.open_now += change


def test_each_page_stays_open_where_it_stopped_until_ctrl_c(monkeypatch, tmp_path):
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    profile = ApplicantProfile.load(profile_with(tmp_path))
    lines, seen = [], []

    def out(line: str) -> None:
        lines.append(line)
        if "Ctrl-C" in line:  # every link has ended: look, then press Ctrl-C
            def later():
                seen.append(site.open_now)
                _thread.interrupt_main()
            threading.Timer(1.0, later).start()

    with FakeJobServer(ARC_FORM, PURE_STORAGE_FORM) as fake:
        site = Watched(fake)
        done = rehearsal.rehearse([ARC_URL, PURE_STORAGE_URL], adapters(site), profile, 2, out=out)

    assert [d.outcome for d in done] == ["ready to submit"] * 2
    assert seen == [2]  # both forms open after the run, on their last page
    assert site.open_now == 0  # Ctrl-C closed them
    assert lines[-1] == "Closed the browsers."


def test_a_captcha_mid_fill_in_a_rehearsal_waits_for_lisul_then_fills_to_the_last_page(monkeypatch, tmp_path):
    # LinkedIn (2026-11-03): the slider stopped the read; Lisul does it, and the rehearsal goes on by itself.
    monkeypatch.setattr(ClaudeFill, "submit", lambda self, page: pytest.fail("a rehearsal clicked Claude fill's submit"))
    phone = RecordingNotifier()
    claude = FakeClaude(driver=CaptchaDriver(solved_ms=1500), essays={"Tell us why": WHY_LUNAR})

    with FakeBambooServer(LUNAR_FORM) as server:
        [done] = rehearse([LUNAR_URL], server, captcha_profile(tmp_path, 1), claude, phone=phone)

    assert done.outcome == "ready to submit", done.why
    assert phone.sent == [("Apply: do the captcha", "Do the captcha on Lunar Outpost. Apply goes on by itself once it's done.")]
    assert [line.split(" ", 1)[1] for line in done.history] == [
        "Paused: do the captcha", "Resumed: the captcha is done; Apply went on from the page"]
    assert server.submissions == []


def test_each_page_held_open_for_lisul_is_his_to_submit_once_its_link_has_ended(monkeypatch, tmp_path):
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    lifted = []
    monkeypatch.setattr(rehearsal, "lift", lambda page, **heard: lifted.append(page.url))
    profile = ApplicantProfile.load(profile_with(tmp_path))

    def out(line: str) -> None:
        if "Ctrl-C" in line:
            threading.Timer(1.0, _thread.interrupt_main).start()

    with FakeJobServer(ARC_FORM) as fake:
        [done] = rehearsal.rehearse([ARC_URL], adapters(fake), profile, out=out)

    assert done.outcome == "ready to submit"  # Apply itself sent nothing
    assert fake.submissions == []
    assert lifted == [ARC_URL]  # then the guard came off the page held for Lisul


class Counted(NeverSubmits):
    """NeverSubmits that counts its fills."""

    def __init__(self, filler):
        super().__init__(filler)
        self.fills = 0

    def fill(self, page, questions, answers):
        self.fills += 1
        return super().fill(page, questions, answers)


class MisreadOnce(Counted):
    """Counted whose first fill reads back a blank first name, so the form
    is filled once more."""

    def __init__(self, filler):
        super().__init__(filler)
        self.pages = []

    def fill(self, page, questions, answers):
        self.pages.append(page)
        readback = super().fill(page, questions, answers)
        return {**readback, "first_name": ""} if self.fills == 1 else readback


def test_a_second_fill_after_a_misread_fills_the_same_window_not_a_new_one(monkeypatch, tmp_path):
    filler = MisreadOnce(GreenhouseFiller())
    monkeypatch.setitem(FILLERS, "greenhouse", filler)

    with FakeJobServer(ARC_FORM) as fake:
        [done] = rehearse([ARC_URL], fake, profile_with(tmp_path))
        browsers = len(fake.workers)  # one browser started per open()

    assert filler.fills == 2
    assert filler.pages[0] is filler.pages[1]
    assert browsers == 1
    assert done.outcome == "ready to submit", done.why


def lisul_on_the_held_page(monkeypatch, clicks):
    """Once Apply hands a page to Lisul, he clicks `clicks(n)`, the buttons
    named, on the nth page handed to him (n from 1)."""
    real, handed = rehearsal.lift, []

    def lift(page, **heard):
        real(page, **heard)
        handed.append(page)
        for name in clicks(len(handed)):
            page.get_by_role("button", name=name).click()
    monkeypatch.setattr(rehearsal, "lift", lift)


def hold_until(site, profile, done: Callable[[list[str]], bool], with_adapters: dict | None = None, url: str = ARC_URL,
               **more) -> list[str]:
    """Rehearse Arc's link (or `url`) with its page held open, then press Ctrl-C once
    `done(lines printed)`; or after two minutes, so a test never hangs.
    `with_adapters` replaces adapters of the test's."""
    lines, ctrl_c = [], threading.Timer(1.0, _thread.interrupt_main)

    def out(line: str) -> None:
        lines.append(line)
        if done(lines) and not ctrl_c.is_alive() and not ctrl_c.finished.is_set():  # once: a later one hits the next test
            ctrl_c.start()
    watchdog = threading.Timer(120, _thread.interrupt_main)
    watchdog.start()
    try:
        rehearsal.rehearse([url], adapters(site, **(with_adapters or {})), profile, out=out, **more)
    finally:
        watchdog.cancel()
        ctrl_c.cancel()
    return lines


def test_lisuls_own_submit_on_a_held_page_is_kept_in_the_tracker_as_submitted(monkeypatch, tmp_path):
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    lisul_on_the_held_page(monkeypatch, lambda n: ["Submit application"])
    profile, tracker = ApplicantProfile.load(profile_with(tmp_path)), InMemoryTracker()
    essays.TOLD[ARC_URL] = {"What did the boat do?": "It floated."}  # his answer to this form's Essay fact

    with FakeJobServer(ARC_FORM) as fake:
        lines = hold_until(fake, profile, lambda lines: "you submitted it" in lines[-1], submitted_to=tracker)
        submissions = fake.submissions

    assert ARC_URL not in essays.TOLD  # never kept past its submit
    assert len(submissions) == 1  # Lisul's, sent from the held page
    [row] = tracker.rows()
    assert (row.status, row.date_applied, row.posting_url) == ("submitted", NOW.date(), ARC_URL)
    assert row.company == "Arc Boat Company" and "You submitted it" in row.reason
    assert any(line.startswith("Arc Boat Company | ") and "you submitted it; it is in the Tracker" in line for line in lines)


def test_lisuls_own_submit_saves_the_record_again_as_submitted_with_its_confirmation(monkeypatch, tmp_path):
    # KLA, 2026-11-03: he submitted the held form himself, and its Record still said held.
    from apply.records import InMemoryRecords

    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    lisul_on_the_held_page(monkeypatch, lambda n: ["Submit application"])
    profile, records = ApplicantProfile.load(profile_with(tmp_path)), InMemoryRecords()

    with FakeJobServer(ARC_FORM) as fake:
        lines = hold_until(fake, profile, lambda lines: "you submitted it" in lines[-1], submitted_to=InMemoryTracker(),
                           with_adapters={"records": records})

    [link] = records.links()
    files = records.files(link)
    assert "- Status: submitted (You submitted it yourself from a rehearsal" in files["README.md"].decode()
    assert files["after-submit.png"].startswith(b"\x89PNG")
    assert any("its Record says submitted" in line for line in lines)


def test_a_held_form_lisul_sends_with_a_missing_fact_open_shows_as_sent_and_leaves_needs_you(monkeypatch, tmp_path):
    # Saronic, 2026-11-04: he sent the held form himself; the tile still asked its Missing facts, so it looked unsent.
    from apply.dashboard import Dashboard, NoFrames

    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    real = rehearsal.lift

    def lift(page, **heard):  # he types the Missing fact on the page, not in the window, and sends it
        real(page, **heard)
        page.get_by_label("Last Name").first.fill("Elvitigala")
        page.get_by_role("button", name="Submit application").click()
    monkeypatch.setattr(rehearsal, "lift", lift)
    rescued = []
    monkeypatch.setattr(rescue.Rescue, "field", lambda self, page, label, value, error: rescued.append(label))
    profile = ApplicantProfile.load(profile_with(tmp_path, **{"identity.legal_last_name": None}))
    asked = []

    class Board(Dashboard):
        late = [("Last Name", "Elvitigala")]  # his answer in the window, given after the form went in

        def update(self, worker, **caption):
            super().update(worker, **caption)
            if caption.get("status") == rehearsal.READY:
                asked.append(list(self.state()["tiles"][0].get("missing") or []))

        def answered(self, worker):
            if self._captions[worker].get("status") == "submitted" and self.late:
                given, self.late = self.late, []
                return given
            return super().answered(worker)

    board = Board(1, NoFrames())
    with FakeJobServer(ARC_FORM) as fake:
        hold_until(fake, profile, lambda lines: "you submitted it" in lines[-1], submitted_to=InMemoryTracker(),
                   with_adapters={"board": board})
        submissions = fake.submissions

    assert len(submissions) == 1 and asked and asked[0]  # held with a Missing fact open, then sent by him
    [tile], items = board.state()["tiles"], board.state()["items"]
    assert tile["tone"] == "submitted" and tile["label"].endswith(("Sent", "sent")) and tile["missing"] == []
    assert "you submitted it; it is in the Tracker" in tile["detail"]
    assert [i["tone"] for i in items] == ["submitted"]  # no card for it waits in Needs you
    assert not board.late and rescued == []  # the late answer filled nothing on the sent form


def test_a_captcha_after_lisuls_own_submit_pushes_him_to_do_it(monkeypatch, tmp_path):
    # Lisul (2026-11-03): in a rehearsal he presses Submit and does the captcha himself; Apply only tells him.
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    lisul_on_the_held_page(monkeypatch, lambda n: ["Submit application"])
    profile, phone, board = ApplicantProfile.load(captcha_profile(tmp_path, 1)), RecordingNotifier(), RecordingBoard()

    with FakeJobServer(ARC_FORM, challenge=True) as fake:
        lines = hold_until(fake, profile, lambda lines: "do the captcha" in lines[-1],
                           with_adapters={"phone": phone, "board": board})
        submissions = fake.submissions

    assert phone.sent == [("Apply: do the captcha", "Do the captcha on Arc Boat Company. "
                                                    "Apply goes on by itself once it's done.")]
    assert any(line.startswith("Arc Boat Company | ") and "do the captcha yourself" in line for line in lines)
    assert (board.captions[0]["status"], board.captions[0]["captcha"]) == ("handoff", True)
    assert submissions == []  # nothing goes until the captcha is done


def test_lever_turning_down_lisuls_own_submit_is_a_bot_block_for_his_own_chrome(monkeypatch, tmp_path):
    # Simbe Robotics, 2026-11-03: Lever's hCaptcha turned the token of the Worker's Chrome down at his Submit.
    monkeypatch.setitem(FILLERS, "lever", NeverSubmits(LeverFiller()))
    lisul_on_the_held_page(monkeypatch, lambda n: ["Submit application"])
    profile, board, tracker = ApplicantProfile.load(profile_with(tmp_path)), RecordingBoard(), InMemoryTracker()

    with FakeLeverServer(IMMUTA_FORM, parse_delay=0.2, refuse=True) as fake:
        lines = hold_until(fake, profile, lambda lines: "in your Chrome" in lines[-1], url=IMMUTA_URL,
                           with_adapters={"board": board}, submitted_to=tracker)
        submissions = fake.submissions

    caption = board.captions[0]
    assert caption["status"] == "handoff" and caption["blocked"] is True
    assert "Immuta blocked Apply's Chrome as a bot (\"There was an error verifying your application\")" in caption["why"]
    assert any(line.startswith("Immuta | ") and "Finish Immuta in your Chrome: the extension fills it" in line
               for line in lines)
    assert submissions == [] and tracker.rows() == []  # nothing went in, so nothing is kept as submitted


def test_lisuls_own_submit_from_a_rehearsal_is_applied_in_his_applications_tracker(monkeypatch, tmp_path):
    # KAN-544: the submit he made goes to WorkIt as Applied, the resume the form was given as its Sent resume.
    from fake_tracker import FakeTracker
    from fake_workit import FakeWorkIt

    from apply import workit
    from apply.tracker import WorkItTracker
    from apply.worker import sent_resume

    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    lisul_on_the_held_page(monkeypatch, lambda n: ["Submit application"])
    profile = ApplicantProfile.load(profile_with(tmp_path))
    resume_name = Path(profile.get("files.resume_pdf")).name

    with FakeWorkIt() as wi, FakeJobServer(ARC_FORM) as fake:
        applications = FakeTracker(wi)
        client = workit.WorkIt(wi.site, tmp_path / "workit-login.json", wi.keychain)
        workit.login(client, wi.browser)
        tracker = WorkItTracker(InMemoryTracker(), workit.WaitingWrites(client, tmp_path / "workit-queue.json"),
                                lambda application_id: sent_resume(application_id, resume_name))
        hold_until(fake, profile, lambda lines: "you submitted it" in lines[-1], submitted_to=tracker)

    assert applications.tracked() == [{"link": ARC_URL, "company": "Arc Boat Company", "stage": "applied",
                                       "sent_resume": resume_name}]


def test_lisuls_submit_sends_his_tailored_resume_and_keeps_that_file_as_the_sent_resume(monkeypatch, tmp_path):
    # KAN-547: the posting has a tailored resume on WorkIt, so the form gets it, by the profile's resume name.
    from fake_tracker import FakeTracker
    from fake_workit import FakeWorkIt

    from apply import tailored, workit
    from apply.tracker import WorkItTracker
    from apply.worker import sent_resume

    monkeypatch.setattr(tailored, "TAILORED", tmp_path / "tailored")
    monkeypatch.setattr(worker, "SENT", tmp_path / "sent")
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    lisul_on_the_held_page(monkeypatch, lambda n: ["Submit application"])
    profile = ApplicantProfile.load(profile_with(tmp_path))
    resume_name = Path(profile.get("files.resume_pdf")).name
    tailored_pdf = b"%PDF-1.7 the resume tailored to Arc"

    with FakeWorkIt() as wi, FakeJobServer(ARC_FORM) as fake:
        applications = FakeTracker(wi)
        applications.tailored(applications.listed(ARC_URL, "Arc Boat Company", "Intern"), tailored_pdf)
        client = workit.WorkIt(wi.site, tmp_path / "workit-login.json", wi.keychain)
        workit.login(client, wi.browser)
        tracker = WorkItTracker(InMemoryTracker(), workit.WaitingWrites(client, tmp_path / "workit-queue.json"),
                                lambda application_id: sent_resume(application_id, resume_name, tmp_path / "sent"))
        hold_until(fake, profile, lambda lines: "you submitted it" in lines[-1], submitted_to=tracker,
                   with_adapters={"tailored": tailored.from_workit(client)})
        submitted = fake.submissions

    assert resume_name in submitted[0].application.values()  # the form got it under the profile's resume name
    [given] = (tmp_path / "sent").glob(f"*/*/{resume_name}")
    assert given.read_bytes() == tailored_pdf
    assert applications.tracked() == [{"link": ARC_URL, "company": "Arc Boat Company", "stage": "applied",
                                       "sent_resume": resume_name}]
    assert [sent.content for sent in applications.sent.values()] == [tailored_pdf]
    assert profile.get("files.resume_pdf").read_bytes() != tailored_pdf  # the profile still names the base resume


def test_a_rehearsal_lisul_does_not_submit_sends_nothing_to_workit(monkeypatch, tmp_path):
    from fake_tracker import FakeTracker
    from fake_workit import FakeWorkIt

    from apply import workit
    from apply.tracker import WorkItTracker

    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    lisul_on_the_held_page(monkeypatch, lambda n: [])
    profile = ApplicantProfile.load(profile_with(tmp_path))

    with FakeWorkIt() as wi, FakeJobServer(ARC_FORM) as fake:
        applications = FakeTracker(wi)
        client = workit.WorkIt(wi.site, tmp_path / "workit-login.json", wi.keychain)
        workit.login(client, wi.browser)
        wi.requests.clear()
        tracker = WorkItTracker(InMemoryTracker(), workit.WaitingWrites(client, tmp_path / "workit-queue.json"),
                                lambda application_id: "")
        hold_until(fake, profile, lambda lines: "Ctrl-C" in lines[-1], submitted_to=tracker)

    assert wi.requests == [] and applications.tracked() == []


class OnePage:
    """A job site whose every page is `html`, in a browser of its own."""

    def __init__(self, html: str):
        self._html = html

    @contextmanager
    def open(self, url: str, worker: int = 0):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                page = browser.new_page()
                page.context.route("**/*", lambda route: route.fulfill(content_type="text/html", body=self._html))
                page.goto(url)  # the guard reloads it
                yield page
            finally:
                browser.close()


SENT = "<button onclick=\"document.body.innerHTML = '<p>Thank you for applying!</p>'{}\">Submit</button>"


# Faults: a sent page that went to about:blank after its confirmation (the confirmation gone) kept its window till the
# run ended (live, 2026-11-26); a pop-up kept a sent form's window for good; a page that went on to another step
# after a confirmation closed under him.
@pytest.mark.parametrize("pop_up, keep_s, closes", [
    ("", 600, True),
    ("; window.open('about:blank')", 600, False),
    ("; setTimeout(() => location.href = 'about:blank', 100)", 600, True),
    ("; window.open('about:blank')", 1.5, True),
    ("; setTimeout(() => document.body.innerHTML = '<p>One more step</p>', 100)", 1.5, False),
])
def test_a_confirmed_page_closes_its_window_after_a_wait_unless_a_pop_up_came(monkeypatch, pop_up, keep_s, closes):
    monkeypatch.setattr(rehearsal, "CLOSE_AFTER_S", 0.5)
    monkeypatch.setattr(rehearsal, "SENT_KEEP_S", keep_s)
    lisul_on_the_held_page(monkeypatch, lambda n: ["Submit"])
    site, release, kept = rehearsal._Kept(OnePage(SENT.format(pop_up)), 0), threading.Event(), []
    threading.Timer(5, release.set).start()  # else: Ctrl-C, after five seconds

    with site.open("https://jobs.example.com/apply"):
        assert not site.hold(release, submitted=kept.append)

    assert len(kept) == 1  # the Tracker heard once
    assert release.is_set() != closes  # closed on its own, or left for Lisul


def resume_pressed_later(turns: int = 4):
    """Lisul presses Resume in the window a few turns after the page was handed to him: by then his own presses on
    it have been heard. Returns the hold's `resume(page)`, and each turn it was asked on."""
    asked = []

    def resume(page) -> bool:
        asked.append(True)
        return len(asked) >= turns
    return resume, asked


def test_resume_goes_on_after_lisul_pressed_apply_now_himself_on_the_held_page(monkeypatch):
    # KAN-690: at a paused sign-in he signed in and pressed the site's own "Apply now" and "Complete" on the held
    # page; Resume, pressed after, must still go on with the page, not be dead for the rest of the hold.
    lisul_on_the_held_page(monkeypatch, lambda n: ["Apply now", "Complete"])
    page = "<form onsubmit='return false'><button>Apply now</button></form><button>Complete</button>"
    site, release = rehearsal._Kept(OnePage(page), 0), threading.Event()
    resume, asked = resume_pressed_later()
    threading.Timer(8, release.set).start()  # else: Ctrl-C, so a test never hangs

    with site.open("https://jobs.example.com/apply"):
        assert site.hold(release, resume=resume) == rehearsal.RESUME

    assert len(asked) == 4 and not release.is_set()


def test_resume_never_drives_a_page_lisul_sent_himself(monkeypatch):
    lisul_on_the_held_page(monkeypatch, lambda n: ["Submit"])
    site, release, kept = rehearsal._Kept(OnePage(SENT.format("")), 0), threading.Event(), []
    resume, _ = resume_pressed_later()
    threading.Timer(4, release.set).start()

    with site.open("https://jobs.example.com/apply"):
        assert site.hold(release, submitted=kept.append, resume=resume) == ""

    assert len(kept) == 1  # sent and kept: Resume, pressed after, went on with nothing


# KAN-781: Oracle Recruiting's sign-in, as its Candidate Experience code draws it (main-minimal.js 2607.26): the email
# step's form and Next, then the code step's form of six one-digit boxes (autocomplete off) with Verify and
# "Send New Code" (live, JPMorgan's, 2026-11-10), then the application. Its Submit leaves the page as it is (no thanks).
ORACLE_PIN = """<form class="pin-code-verification" onsubmit="return false"><p>We've sent a verification code to: t***@example.com.
  Paste it here to verify your identity.</p><div class="pin-code-input">{boxes}</div>
  <button type="submit" class="apply-flow-dialog__button" onclick="{verified}"><span class="button__label">Verify</span></button>
  <button class="pin-code-form__action-button" type="button">Send New Code</button></form>""".format(
    boxes="".join(f'<div class="pin-code-input__segment"><input class="input-row__control pin-code-input__input" type="text" '
                  f'inputmode="numeric" autocomplete="off" pattern="[0-9]*" id="pin-code-{n}" '
                  f'aria-label="Enter verification code digit {n} of six."></div>' for n in range(1, 7)),
    verified="document.body.innerHTML = T.form")
ORACLE_FORM = """<h2>Contact Information</h2><form onsubmit="return false"><label>First Name <input></label>
  <label>Resume <input type="file"></label><textarea aria-label="Why us?"></textarea>
  <button type="submit">Submit</button></form>"""
ORACLE = f"""<form onsubmit="return false"><h1>Enter your email to get started</h1><label>Email Address <input type="email"></label>
  <label><input type="checkbox" id="legal-disclaimer-checkbox"> I agree</label>
  <button type="submit" class="apply-flow-pagination__button"
    onclick="document.body.innerHTML = T.pin"><span>Next</span></button></form>
  <template id="pin">{ORACLE_PIN}</template><template id="form">{ORACLE_FORM}</template>
  <script>const T = {{pin: pin.innerHTML, form: form.innerHTML}}; pin.remove(); form.remove();</script>"""
# Oracle's inline code step: the code boxes inside the application's own first section, beside its answers.
ORACLE_INLINE = """<h2>Contact Information</h2><form onsubmit="return false"><label>First Name <input></label>
  <label>Resume <input type="file"></label><textarea aria-label="Why us?"></textarea>{}</form>""".format(
    ORACLE_PIN.replace("onclick=", "data-x=").replace("<form", "<div").replace("</form>", "</div>"))


def lisul_signs_in_to_oracle(monkeypatch, then: tuple[str, ...] = ()):
    """On the held Oracle page, Lisul types his email, presses Next, asks for a new code, types it and presses Verify,
    then presses each button of `then`."""
    real = rehearsal.lift

    def lift(page, **heard):
        real(page, **heard)
        if page.locator("input[type=email]").count():
            page.fill("input[type=email]", "t@example.com")
            page.get_by_role("button", name="Next").click()
        page.get_by_role("button", name="Send New Code").click()
        for n, digit in enumerate("482913", 1):
            page.fill(f"#pin-code-{n}", digit)
        page.get_by_role("button", name="Verify").click()
        for name in then:
            page.get_by_role("button", name=name).click()
    monkeypatch.setattr(rehearsal, "lift", lift)


@pytest.mark.parametrize("html", [ORACLE, ORACLE_INLINE], ids=["code step", "inline code step"])
def test_resume_goes_on_after_lisul_signs_in_to_oracle_on_the_held_page(monkeypatch, html):
    # KAN-781, JPMorgan's Oracle, live: his "Send New Code" on the code step was taken for the application's Submit,
    # and Resume answered "You pressed Submit on the form".
    lisul_signs_in_to_oracle(monkeypatch)
    site, release, sent = rehearsal._Kept(OnePage(html), 0), threading.Event(), []
    resume, asked = resume_pressed_later()
    threading.Timer(8, release.set).start()

    with site.open("https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/1/apply/email"):
        assert site.hold(release, "", resume=resume, sent=lambda: sent.append(True)) == rehearsal.RESUME

    assert len(asked) == 4 and sent == [] and not release.is_set()


def test_the_applications_own_submit_after_an_oracle_sign_in_still_ends_resume(monkeypatch):
    lisul_signs_in_to_oracle(monkeypatch, then=("Submit",))
    site, release, sent = rehearsal._Kept(OnePage(ORACLE), 0), threading.Event(), []
    resume, _ = resume_pressed_later()
    threading.Timer(4, release.set).start()

    with site.open("https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/1/apply/email"):
        assert site.hold(release, "", resume=resume, sent=lambda: sent.append(True)) == ""

    assert sent == [True]  # his Submit: Resume goes on no more, and the window says so


def test_a_thanks_page_after_a_press_read_as_a_sign_ins_still_ends_resume(monkeypatch):
    # The backstop: a press the page read as a sign-in's that the job system confirms sent the form is his Submit.
    lisul_on_the_held_page(monkeypatch, lambda n: ["Submit"])
    page = """<form onsubmit="return false"><input type=password aria-label=Password>
      <button onclick="document.body.innerHTML = '<p>Thank you for applying!</p>'">Submit</button></form>"""
    site, release, kept = rehearsal._Kept(OnePage(page), 0), threading.Event(), []
    resume, _ = resume_pressed_later()
    threading.Timer(4, release.set).start()

    with site.open("https://jobs.example.com/apply"):
        assert site.hold(release, submitted=kept.append, resume=resume) == ""

    assert len(kept) == 1


def test_a_held_page_lisul_does_not_submit_leaves_the_tracker_alone(monkeypatch, tmp_path):
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    lisul_on_the_held_page(monkeypatch, lambda n: [])
    profile, tracker = ApplicantProfile.load(profile_with(tmp_path)), InMemoryTracker()

    with FakeJobServer(ARC_FORM) as fake:
        hold_until(fake, profile, lambda lines: "Ctrl-C" in lines[-1], submitted_to=tracker)

    assert tracker.rows() == []


def test_fill_again_on_a_held_page_fills_its_form_once_more_in_the_same_browser(monkeypatch, tmp_path):
    filler = Counted(GreenhouseFiller())
    monkeypatch.setitem(FILLERS, "greenhouse", filler)
    lisul_on_the_held_page(monkeypatch, lambda n: ["Fill again"] if n == 1 else [])
    profile = ApplicantProfile.load(profile_with(tmp_path))

    with FakeJobServer(ARC_FORM) as fake:
        lines = hold_until(fake, profile, lambda lines: sum("ready to submit" in line for line in lines) == 2)
        submissions = fake.submissions

    assert filler.fills == 2
    assert sum("ready to submit" in line for line in lines) == 2  # a summary line for each fill
    assert submissions == []


def test_fill_again_from_the_window_fills_its_form_once_more_with_no_click_on_the_page(monkeypatch, tmp_path):
    from apply.dashboard import Dashboard, NoFrames, Refused

    filler = Counted(GreenhouseFiller())
    monkeypatch.setitem(FILLERS, "greenhouse", filler)
    lisul_on_the_held_page(monkeypatch, lambda n: [])  # he clicks nothing there
    profile = ApplicantProfile.load(profile_with(tmp_path))

    with FakeJobServer(ARC_FORM) as fake, Dashboard(1, NoFrames()) as board:
        def press() -> None:  # as `apply fill-again` does, from outside the Worker's page
            while True:
                try:
                    board.fill_again("tile-0")
                    return
                except Refused:
                    time.sleep(0.2)  # not held yet
        threading.Thread(target=press, daemon=True).start()
        hold_until(fake, profile, lambda lines: sum("ready to submit" in line for line in lines) == 2,
                   with_adapters={"board": board})
        submissions = fake.submissions

    assert filler.fills == 2 and submissions == []


class FailsOnce(Counted):
    """Counted whose first fill fails, as a page that broke mid-form."""

    def fill(self, page, questions, answers):
        if not self.fills:
            self.fills += 1
            raise RuntimeError("the page broke")
        return super().fill(page, questions, answers)


def test_try_again_in_a_student_window_fills_a_failed_form_anew(monkeypatch, tmp_path):
    """KAN-873: a Student run has no Ask Claude, so its held page is never askable; its Worker still holds the
    failed form's page, and Try again in the window (`/fill-again`) fills it anew."""
    from apply import build
    from apply.dashboard import Dashboard, NoFrames, Refused

    monkeypatch.setattr(build, "STUDENT", True)
    filler = FailsOnce(GreenhouseFiller())
    monkeypatch.setitem(FILLERS, "greenhouse", filler)
    lisul_on_the_held_page(monkeypatch, lambda n: [])
    profile = ApplicantProfile.load(profile_with(tmp_path))
    seen = []

    with FakeJobServer(ARC_FORM) as fake, Dashboard(1, NoFrames()) as board:
        def press() -> None:
            for _ in range(300):
                try:
                    board.fill_again("tile-0")
                    seen.append(board.state()["tiles"][0]["tone"])
                    return
                except Refused:
                    time.sleep(0.2)  # not held yet
        threading.Thread(target=press, daemon=True).start()
        lines = hold_until(fake, profile, lambda lines: any("ready to submit" in line for line in lines),
                           with_adapters={"board": board})
        submissions = fake.submissions

    assert seen == ["failed"]  # tried again from the failed form, not a held one
    assert filler.fills == 2 and any("ready to submit" in line for line in lines) and submissions == []


def test_a_field_the_filler_cannot_fill_is_reported_and_the_rest_still_filled(tmp_path):
    profile = profile_with(tmp_path, **{"education.school": "Example State University"})
    # A board whose school search names two Example States: the Filler won't guess between them.
    with board_listing_schools(tmp_path, ["Example State University - SUNY", "Example State University - Southampton"]) as board:
        [done] = rehearse([ANDURIL_URL], board, profile)

    assert done.outcome == "ready to submit"
    assert "Not filled: school--0: Greenhouse's search offered several named like it" in done.why
    assert done.filled >= 5  # name, email, phone, résumé, work authorization...
    assert board.submissions == []


def test_a_summary_is_one_line_however_long_the_error():
    error = "TimeoutError: Timeout 30000.0ms exceeded.\n=== logs ===\nwaiting for navigation\n" + "x" * 1000
    done = rehearsal.Rehearsed(Posting("p", "Snap", "Intern", "https://wd1.myworkdaysite.com/x"), "failed", error)

    assert "\n" not in done.line() and len(done.line()) < 500


def test_each_links_tile_on_the_dashboard_says_what_it_is_and_how_it_ended(monkeypatch, tmp_path):
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    board = RecordingBoard()

    with FakeJobServer(ARC_FORM) as fake:
        [done] = rehearse([ARC_URL], fake, profile_with(tmp_path), board=board)

    files = board.captions[0].pop("files")  # a kept copy of each file the form was sent
    assert files and all(Path(f["path"]).is_file() for f in files)
    assert board.captions[0].pop("posting_url").startswith("http")  # so the window can link the Posting
    assert board.captions[0].pop("link") == ARC_URL  # the link it was given, which the window finds its logo by
    assert board.captions[0].pop("application_id")
    assert board.captions[0].pop("verifying") is False  # verified once it was filled, before it stopped
    assert board.captions[0].pop("verification")["state"] in ("verified", "flagged")
    # The stuck watch's last word (apply.stuck): read only while a tile is filling.
    assert isinstance(board.captions[0].pop("doing"), str)
    assert isinstance(board.captions[0].pop("progress_at"), float)
    assert board.captions[0].pop("waiting") is False
    # Nothing paused, waited, regenerated or refused it as a bot.
    assert board.captions[0].pop("history") == []
    assert board.captions[0].pop("written") == []
    assert board.captions[0].pop("blocked") is False
    assert board.captions[0].pop("where") == {}
    # What the student page's held card lists (worker._Planned.listed): each answer, where it came from, and the
    # resume by its name only, never its path on the Mac. The review changed nothing.
    answers = {a["question"]: a for a in board.captions[0].pop("answers")}
    assert [(answers[q]["from"], answers[q]["topic"]) for q in ("Resume/CV", "Cover Letter")] == [
        ("profile", "file"), ("written", "file")]
    assert not any("/" in answers[q]["answer"] for q in ("Resume/CV", "Cover Letter"))
    assert answers["Are you legally authorized to work in the United States?"]["topic"] == "legal"
    assert board.captions[0].pop("fixed") == []
    assert board.captions == {0: {
        "company": "Arc Boat Company", "role": "Software Engineering Intern", "job_system": "greenhouse",
        "status": "ready to submit", "stage": "", "line": done.line(), "why": done.why,
        "filled": done.filled, "asked": done.asked, "missing": list(done.missing), "drafted": [],
        "choices": {}, "required": {}, "planned": {}, "again": False,
    }}
    assert done.asked > 0


def test_a_failure_keeps_its_traceback_in_the_log(monkeypatch, tmp_path, capsys):
    def blow_up(*args, **kwargs):
        raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr(rehearsal, "by_filler", blow_up)
    with FakeJobServer(ARC_FORM) as fake:
        [done] = rehearse([ARC_URL], fake, profile_with(tmp_path))

    assert done.outcome == "failed" and "PermissionError" in done.why
    log = capsys.readouterr().err
    assert "Traceback" in log and "blow_up" in log


def test_a_workday_step_left_with_a_missing_fact_lists_it_where_the_rehearsal_stopped(monkeypatch, tmp_path):
    # Snap's degree list has B.A. and B.S., not the profile's Bachelor's Degree: no guess between them.
    monkeypatch.setitem(FILLERS, "workday", NeverSubmittingWorkday)

    world = experience_profile()
    with FakeWorkdayServer(XCEL_FORM, steps=EXPERIENCE_STEPS) as server:
        [done] = rehearse([XCEL_URL], server, world.profile, records=FolderRecords(tmp_path / "rehearsals"))

    assert done.outcome == "handoff" and "won't leave its 'My Experience' step" in done.why and "Degree" in done.why
    assert done.missing == ("Education 1 / Degree",)
    assert "Missing facts: Education 1 / Degree" in done.line()
    # Its Record keeps what was planned and shown up to the step it stopped on (ASML's had none, live).
    assert 0 < done.filled < done.asked
    rows = json.loads((Path(done.record) / "answers.json").read_text())
    assert any(r["question"] == "Education 1 / Degree" and r["on_page"] in (None, "") for r in rows)
    assert server.submissions == []


def test_a_failure_and_each_missing_fact_leave_a_repair_request(monkeypatch, tmp_path):
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    profile = profile_with(tmp_path, **{"identity.email": None})
    repairs = RepairRequests(tmp_path / "repairs")

    with FakeJobServer(ARC_FORM) as fake:
        rehearse([ARC_URL], fake, profile, repairs=repairs)
    [email] = repairs.waiting()
    assert (email.kind, email.missing, email.posting_url) == ("missing fact", ["Email"], ARC_URL)
    assert any(q["label"] == "Email" for q in email.questions)

    def blow_up(*args, **kwargs):
        raise PermissionError(1, "Operation not permitted")

    monkeypatch.setattr(rehearsal, "by_filler", blow_up)
    with FakeJobServer(ARC_FORM) as fake:
        rehearse([ARC_URL], fake, profile, repairs=repairs)
    [failure] = [r for r in repairs.waiting() if r.kind == "failure"]
    assert failure.failure.startswith("PermissionError")
    assert "blow_up" in failure.traceback


def test_once_every_link_has_ended_the_rehearsal_says_so_before_holding_the_pages(monkeypatch, tmp_path):
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    ended = []

    with FakeJobServer(ARC_FORM) as fake:
        rehearsal.rehearse([ARC_URL, ARC_URL], adapters(fake), ApplicantProfile.load(profile_with(tmp_path)), 2,
                           keep_open=False, out=ended.append, on_done=lambda: ended.append("done"))

    assert len(ended) == 3 and ended[-1] == "done"  # where `apply repair` starts, in the background


class StartsLate:
    """A real Filler that notes when each fill starts; its first Question set is slow to read."""

    def __init__(self, filler, slow: float):
        self._filler, self._slow, self.started = filler, slow, []
        self._first = threading.Lock()

    def question_set(self, url, site):
        if self._first.acquire(blocking=False):
            import time
            time.sleep(self._slow)
        return self._filler.question_set(url, site)

    def fill(self, page, questions, answers):
        import time
        self.started.append(time.monotonic())
        return self._filler.fill(page, questions, answers)

    def submit(self, page):
        pytest.fail("a rehearsal called the Filler's submit")


class PressesStartLater(RecordingBoard):
    """A window whose Start Lisul presses `after` seconds once it shows."""

    def __init__(self, after: float):
        super().__init__()
        self._after, self.pressed = after, None

    def wait_for_start(self, timeout: float) -> None:
        import time
        self.run(start="ready")
        time.sleep(self._after)
        self.pressed = time.monotonic()


def test_together_holds_every_form_until_all_are_open_and_start_is_pressed_then_fills_them_at_once(
        monkeypatch, tmp_path):
    filler = StartsLate(GreenhouseFiller(), slow=1.5)
    monkeypatch.setitem(FILLERS, "greenhouse", filler)
    board = PressesStartLater(after=1.0)

    with FakeJobServer(ARC_FORM) as fake:
        lines = []
        done = rehearsal.rehearse([ARC_URL, ARC_URL], adapters(fake, board=board),
                                  ApplicantProfile.load(profile_with(tmp_path)), 1,
                                  keep_open=False, out=lines.append, together=True)

    assert [d.outcome for d in done] == ["ready to submit"] * 2
    first, second = sorted(filler.started)
    assert second - first < 0.5  # the quick link waited for the slow one's form
    assert first >= board.pressed  # and neither filled before Start
    assert [r["start"] for r in board.runs if "start" in r] == ["waiting", "ready"]


def test_without_together_a_quick_form_fills_without_waiting(monkeypatch, tmp_path):
    filler = StartsLate(GreenhouseFiller(), slow=1.5)
    monkeypatch.setitem(FILLERS, "greenhouse", filler)

    with FakeJobServer(ARC_FORM) as fake:
        rehearse([ARC_URL, ARC_URL], fake, profile_with(tmp_path), workers=2)

    first, second = sorted(filler.started)
    assert second - first > 1.0


def test_without_together_start_is_never_asked_for(monkeypatch, tmp_path):
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    board = RecordingBoard()

    with FakeJobServer(ARC_FORM) as fake:
        rehearse([ARC_URL], fake, profile_with(tmp_path), board=board)

    assert not [r for r in board.runs if "start" in r]


def test_the_window_counts_a_link_queued_only_until_its_worker_starts_it(monkeypatch, tmp_path):
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    board = RecordingBoard()

    with FakeJobServer(ARC_FORM) as fake:
        rehearse([ARC_URL, ARC_URL], fake, profile_with(tmp_path), board=board)

    assert [r["queued"] for r in board.runs if "queued" in r] == [2, 1, 0]


class SignsInToRead(StartsLate):
    """A Filler whose Question set is read only after signing in, as Workday's is."""

    signs_in_to_read = True

    def question_set(self, url, site):
        import time
        self.read_at = time.monotonic()
        return super().question_set(url, site)


def test_together_holds_a_filler_that_signs_in_to_read_before_it_signs_in(monkeypatch, tmp_path):
    filler = SignsInToRead(GreenhouseFiller(), slow=0)
    monkeypatch.setitem(FILLERS, "greenhouse", filler)
    board = PressesStartLater(after=1.0)

    with FakeJobServer(ARC_FORM) as fake:
        rehearsal.rehearse([ARC_URL], adapters(fake, board=board), ApplicantProfile.load(profile_with(tmp_path)), 1,
                           keep_open=False, out=lambda line: None, together=True)

    assert filler.read_at >= board.pressed


class PlansSlowly(FakeClaude):
    """A Claude whose every call notes the pages open at that moment."""

    def __init__(self, site):
        super().__init__()
        self._site, self.open_while_asked = site, []

    def ask_kind(self, kind, data):
        self.open_while_asked.append(len(getattr(self._site, "opened", [])))
        return super().ask_kind(kind, data)


def test_a_rehearsal_opens_its_form_before_claude_writes_its_answers(monkeypatch, tmp_path):
    opened = []
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))

    with FakeJobServer(ARC_FORM) as fake:
        real_open = fake.open

        def open_and_note(url, *args, **kwargs):
            opened.append(url)
            return real_open(url, *args, **kwargs)

        monkeypatch.setattr(fake, "open", open_and_note)
        fake.opened = opened
        claude = PlansSlowly(fake)
        rehearse([ARC_URL], fake, profile_with(tmp_path), claude=claude)

    assert claude.open_while_asked and all(n > 0 for n in claude.open_while_asked)


def test_a_filler_that_signs_in_to_read_shows_its_posting_while_it_waits_for_start(monkeypatch, tmp_path):
    filler = SignsInToRead(GreenhouseFiller(), slow=0)
    monkeypatch.setitem(FILLERS, "greenhouse", filler)
    opened = []

    class NotesOpenAtStart(PressesStartLater):
        def wait_for_start(self, timeout):
            opened.append(len(fake_opened))
            super().wait_for_start(timeout)

    fake_opened = []
    board = NotesOpenAtStart(after=0)
    with FakeJobServer(ARC_FORM) as fake:
        real_open = fake.open
        monkeypatch.setattr(fake, "open", lambda url, *a, **k: fake_opened.append(url) or real_open(url, *a, **k))
        rehearsal.rehearse([ARC_URL], adapters(fake, board=board), ApplicantProfile.load(profile_with(tmp_path)), 1,
                           keep_open=False, out=lambda line: None, together=True)

    assert opened == [1]  # its page was open, and only it, when Start was asked for


def test_together_tiles_say_getting_ready_then_ready_then_filling(monkeypatch, tmp_path):
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    stages = []

    class NotesStages(PressesStartLater):
        def update(self, worker, **caption):
            if "stage" in caption:
                stages.append(caption["stage"])
            super().update(worker, **caption)

    with FakeJobServer(ARC_FORM) as fake:
        rehearsal.rehearse([ARC_URL], adapters(fake, board=NotesStages(after=0)),
                           ApplicantProfile.load(profile_with(tmp_path)), 1, keep_open=False, out=lambda line: None,
                           together=True)

    assert stages == ["getting ready", "ready", ""]


def test_a_filling_tile_held_for_start_says_getting_ready_then_ready():
    from apply.dashboard import verdict
    assert verdict({"status": "filling", "stage": "getting ready"})["label"] == "Getting ready"
    assert verdict({"status": "filling", "stage": "ready"})["label"] == "Ready"
    assert verdict({"status": "filling", "stage": ""})["label"] == "Filling"


def test_missing_facts_reach_the_window_before_claude_is_asked_anything(monkeypatch, tmp_path):
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    profile = profile_with(tmp_path, **{"identity.email": None, "identity.legal_last_name": None})
    claude, heard = FakeClaude(), []

    class Board(RecordingBoard):
        def update(self, worker, **caption):
            if caption.get("missing") and caption.get("status") is None:  # while its form fills
                heard.append((tuple(caption["missing"]), len(claude.asked)))
            super().update(worker, **caption)

    board = Board()
    with FakeJobServer(ARC_FORM) as fake:
        [done] = rehearse([ARC_URL], fake, profile, claude, board=board)

    assert heard[0] == (("Last Name", "Email"), 0)  # asked of Lisul with no Claude call made yet
    assert board.captions[0]["required"] == {"Last Name": True, "Email": True}  # the form's own flags
    assert done.missing == ("Last Name", "Email") and claude.asked  # Claude still reviewed the form after


def test_an_answer_given_in_the_window_is_filled_into_the_held_form(monkeypatch, tmp_path):
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    profile = profile_with(tmp_path, **{"identity.email": None, "identity.legal_last_name": None})
    rescued = []

    held, notes = [], []

    def field(self, page, label, value, error):  # Claude's one-field fill, on the page held open
        rescued.append((label, value, page.url))
        held.append(page)
        notes.append(page.inner_text("#apply-rehearsal-blocked"))
        return True

    monkeypatch.setattr(rescue.Rescue, "field", field)

    class Board(RecordingBoard):
        given = [("Email", "lisul@example.com"), ("Pronouns", "he/him")]  # Pronouns: not a field this form left blank

        before = None  # the form's filled count when the answers were given

        def answered(self, worker):
            given, self.given = self.given, []
            if given:
                self.before = self.captions[worker]["filled"]
            elif held:  # the answer filled: what the note says now, then Lisul closes the window
                notes.append(held[0].inner_text("#apply-rehearsal-blocked"))
                held.pop().close()
            return given

    board = Board()
    with FakeJobServer(ARC_FORM) as fake:
        rehearsal.rehearse([ARC_URL], adapters(fake, board=board), ApplicantProfile.load(profile), 1,
                           keep_open=True, out=lambda line: None)

    assert [(label, value) for label, value, _ in rescued] == [("Email", "lisul@example.com")]
    assert board.captions[0]["missing"] == ["Last Name"]  # what is still left blank
    assert board.captions[0]["filled"] == board.before + 1  # the window counts the field filled
    assert "Please fill in: Last Name, Email" in notes[0] and "Email" not in notes[1] and "Last Name" in notes[1]  # the note on the form too
    assert fake.submissions == []


def test_a_file_attached_in_the_window_is_listed_on_its_tile_kept_by_its_name_and_recorded(monkeypatch, tmp_path):
    # Live (Appian): a writing sample attached from Needs you was on the form, but not in the tile's
    # files, the Record or its README, and the line still listed it as a Missing fact.
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    profile = profile_with(tmp_path, **{"identity.email": None})
    picked = tmp_path / "picked" / "Lisul_Elvitigala_Writing_Sample.pdf"
    picked.parent.mkdir()
    picked.write_bytes(b"%PDF-1.4 a writing sample")
    rescued, held = [], []

    def field(self, page, label, value, error):
        rescued.append(value)
        held.append(page)
        return True

    monkeypatch.setattr(rescue.Rescue, "field", field)

    class Board(RecordingBoard):
        given = [("Email", picked)]

        def answered(self, worker):
            given, self.given = self.given, []
            if not given and held:
                held.pop().close()
            return given

    board = Board()
    with FakeJobServer(ARC_FORM) as fake:
        rehearsal.rehearse([ARC_URL], adapters(fake, board=board, records=FolderRecords(tmp_path / "rehearsals")),
                           ApplicantProfile.load(profile), 1, keep_open=True, out=lambda line: None)

    [attached] = [f for f in board.captions[0]["files"] if f["label"] == "Email"]
    kept = Path(attached["path"])
    assert attached["name"] == kept.name == "Lisul_Elvitigala_Writing_Sample.pdf"
    assert kept.read_bytes() == b"%PDF-1.4 a writing sample" and kept.parent.parent.parent == worker.SENT
    assert rescued == [kept]  # the form is given the kept copy, by its own name
    assert len(board.captions[0]["files"]) > 1  # the résumé still listed beside it
    [row] = [r for r in json.loads((rehearsal_record(tmp_path) / "answers.json").read_text()) if r["question"] == "Email"]
    assert row["planned"] == row["on_page"] == "Lisul_Elvitigala_Writing_Sample.pdf"
    readme = (rehearsal_record(tmp_path) / "README.md").read_text()
    assert "| Email | Lisul_Elvitigala_Writing_Sample.pdf | Lisul_Elvitigala_Writing_Sample.pdf |" in readme
    assert "Missing facts: none" in board.captions[0]["line"]


def test_add_context_and_regenerate_on_the_form_writes_that_answer_again_into_its_field(monkeypatch, tmp_path):
    # KAN-599: Lisul reads Claude's essay on the held form, presses the small button beside it, types more
    # context and presses Regenerate. Claude writes that one answer again into the field; nothing is sent.
    from test_regenerate import CONTEXT, EARLIER, LATER

    from apply import home
    monkeypatch.setitem(FILLERS, "lever", NeverSubmits(LeverFiller()))
    mission = "What about our mission excites you?"
    claude = FakeClaude(essays={mission: [EARLIER, LATER]})
    pages, seen = [], {}
    lift = rehearsal.lift
    monkeypatch.setattr(rehearsal, "lift", lambda page, **more: (pages.append(page), lift(page, **more))[1])

    class Board(RecordingBoard):
        pressed = False

        def answered(self, worker):  # on the held page's own thread, every half second
            if not pages:
                return []
            page, [written] = pages[0], [w for w in self.captions[worker]["written"] if w["label"] == mission]
            field = page.locator(f'[data-apply-written="{written["name"]}"]')
            mine = page.locator(f'#apply-regenerate [data-for="{written["name"]}"]')
            if not self.pressed:
                field.wait_for(timeout=5_000)
                seen["before"], seen["offered"] = field.input_value(), sorted(w["kind"] for w in self.captions[worker]["written"])
                field.scroll_into_view_if_needed()
                mine.get_by_role("button", name="Add context and regenerate").click()
                mine.locator("textarea").fill(CONTEXT)
                mine.get_by_role("button", name="Regenerate", exact=True).click()
                self.pressed = True
            elif not written["state"]:  # written again
                seen["after"], seen["read_only"] = field.input_value(), field.evaluate("el => el.readOnly")
                seen["note"] = mine.inner_text()
                page.close()  # Lisul is done with it
            return []

        def update(self, worker, **caption):
            if any(w.get("state") == "working" for w in caption.get("written") or []):
                seen["working"] = pages[0].locator('[data-apply-written]').evaluate_all(
                    "boxes => boxes.filter(el => el.readOnly).length")
            super().update(worker, **caption)

    board = Board()
    lines = []
    with FakeLeverServer(HERMEUS_FORM) as fake:
        rehearsal.rehearse([HERMEUS_URL], adapters(fake, claude, board=board, records=FolderRecords(tmp_path / "rehearsals")),
                           ApplicantProfile.load(profile_with(tmp_path)), 1, keep_open=True, out=lines.append)

    assert seen["offered"] == ["draft", "draft", "essay", "essay"]  # each answer Claude wrote; no pick, no profile fact
    assert seen["before"] == EARLIER and seen["working"] == 1  # only that field shows it is being written again
    assert seen["after"] == LATER and seen["read_only"] is False  # the new answer, his to edit
    assert "New answer from your context" in seen["note"]
    [written] = [w for w in board.captions[0]["written"] if w["label"] == mission]
    assert (written["text"], written["kind"], written["state"]) == (LATER, "essay", "")
    assert any(f"regenerated '{mission}' with your context" in line for line in lines)
    assert f'- For "{mission}" at Hermeus: {CONTEXT}' in home.STORY_BANK.read_text()
    [row] = [r for r in json.loads((rehearsal_record(tmp_path) / "answers.json").read_text()) if r["question"] == mission]
    assert row["planned"] == row["on_page"] == LATER  # the Record keeps the new answer
    readme = (rehearsal_record(tmp_path) / "README.md").read_text()
    assert f"Regenerated '{mission}' with your context" in readme
    assert LATER in (rehearsal_record(tmp_path) / "essays.md").read_text()
    assert fake.submissions == []


def rehearsal_record(tmp_path) -> Path:
    [readme] = (tmp_path / "rehearsals").glob("*/*/README.md")
    return readme.parent


def test_a_form_that_never_shows_fails_before_claude_plans_it(tmp_path):
    # Overland AI's Rippling form (seen live 2026-11-27) showed "We're experiencing an issue" in place of its
    # fields; the rehearsal planned every answer with Claude, then waited out the engine, and failed after 275 s.
    claude = FakeClaude()
    with FakeRipplingServer(RIPPLING_FORM, crashes=99) as fake:
        [done] = rehearse([RIPPLING_URL], fake, profile_with(tmp_path), claude)

    assert done.outcome == "failed"
    assert "the form never showed" in done.why and "experiencing an issue" in done.why
    assert (claude.calls, claude.kinds, done.tokens) == ([], [], 0)
    assert fake.submissions == []


def test_no_fill_engine_stops_its_link_on_one_line_before_the_form_opens(monkeypatch, tmp_path, capsys):
    from apply import fill_engine

    def no_engine(*args, **kwargs):
        raise fill_engine.EngineMissing("the Fill engine isn't built at /nowhere: run `git submodule update --init`")

    monkeypatch.setattr(rehearsal, "resolve", no_engine)
    repairs = RepairRequests(tmp_path / "repairs")
    lines = []
    with FakeJobServer(ARC_FORM) as fake:
        [done] = rehearsal.rehearse([ARC_URL], adapters(fake, repairs=repairs), ApplicantProfile.load(profile_with(tmp_path)),
                                    1, keep_open=False, out=lines.append)

    assert done.outcome == "failed"
    [line] = lines
    assert "git submodule update --init" in line and "\n" not in line
    assert "Traceback" not in capsys.readouterr().err
    assert repairs.all() == []


def test_a_setup_error_stops_its_link_on_one_line_and_leaves_no_repair_request(monkeypatch, tmp_path, capsys):
    from apply.adapters import SetupError

    def logged_out(*args, **kwargs):
        raise SetupError("Claude isn't logged in: run `claude auth login` in a terminal, then try again")

    monkeypatch.setattr(rehearsal, "by_filler", logged_out)
    repairs = RepairRequests(tmp_path / "repairs")
    lines = []
    with FakeJobServer(ARC_FORM) as fake:
        [done] = rehearsal.rehearse([ARC_URL], adapters(fake, repairs=repairs), ApplicantProfile.load(profile_with(tmp_path)),
                                    1, keep_open=False, out=lines.append)

    assert done.outcome == "failed"
    [line] = lines
    assert "claude auth login" in line and "\n" not in line
    assert "Traceback" not in capsys.readouterr().err
    assert repairs.all() == []


class AppliedTo:
    """The already applied check (KAN-621), answering for every link: applied on 2026-10-28, or not; and why
    WorkIt could not be checked."""

    def __init__(self, applied: bool = True, problem: str = ""):
        from apply.already_applied import Applied

        self._found = Applied(datetime(2026, 10, 28).date(), "your Applications Tracker on WorkIt: applied") \
            if applied else None
        self._problem = problem
        self.asked: list[str] = []

    def of(self, posting, *links):
        self.asked.append(posting.url)
        return self._found

    def problem(self):
        return self._problem


def test_a_link_already_applied_to_ends_before_its_form_opens(monkeypatch, tmp_path):
    # Astranis, 2026-11-04: the rehearsal filled a form he had applied to, Submit live, and he sent it again.
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    board, lines, check = RecordingBoard(), [], AppliedTo()

    with FakeJobServer(ARC_FORM) as fake:
        [done] = rehearsal.rehearse([ARC_URL], adapters(fake, board=board, applied_before=check),
                                    ApplicantProfile.load(profile_with(tmp_path)), keep_open=False, out=lines.append)
        opened = list(fake.workers)

    assert opened == []  # no browser, no form
    assert check.asked == [ARC_URL]
    assert done.outcome == "already applied"
    assert lines == ["Arc Boat Company | Software Engineering Intern | greenhouse | Already applied on 2026-10-28 "
                     "(your Applications Tracker on WorkIt: applied); Apply didn't open the form. "
                     "`apply rehearse --force` rehearses it anyway, with Submit blocked"]
    caption = board.captions[0]
    assert (caption["status"], caption["why"]) == (
        "already applied", "Already applied on 2026-10-28 (your Applications Tracker on WorkIt: applied)")


def test_a_check_that_could_not_run_is_said_in_the_window_and_the_terminal(monkeypatch, tmp_path):
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    board, lines = RecordingBoard(), []
    check = AppliedTo(applied=False, problem="you are not signed in to WorkIt (run `uv run apply login`)")

    with FakeJobServer(ARC_FORM) as fake:
        [done] = rehearsal.rehearse([ARC_URL], adapters(fake, board=board, applied_before=check),
                                    ApplicantProfile.load(profile_with(tmp_path)), keep_open=False, out=lines.append)

    said = ("Couldn't check your Applications Tracker on WorkIt for jobs you already applied to: you are not signed "
            "in to WorkIt (run `uv run apply login`). Apply checked only its own Tracker and Records")
    assert {"unchecked": said} in board.runs
    assert lines[0] == said
    assert done.outcome == "ready to submit"  # not applied to: it fills


def test_force_rehearses_it_but_submit_stays_blocked_until_the_red_note_is_dismissed(monkeypatch, tmp_path):
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    lisul_on_the_held_page(monkeypatch, lambda n: ["Submit application"])  # once the guard is off
    real, seen = rehearsal.warn_applied, {}

    def warned(page, day, dismissed=None):
        real(page, day, dismissed)
        seen["note"] = page.locator("#apply-already-applied").inner_text()
        page.get_by_role("button", name="Submit application").click()  # blocked
        page.wait_for_timeout(500)
        seen["sent before"] = len(fake.submissions)
        page.get_by_role("button", name="Dismiss").click()
        seen["sent after one press"] = len(fake.submissions)
        page.get_by_role("button", name="Yes, I’m sure: unblock this page").click()
    monkeypatch.setattr(rehearsal, "warn_applied", warned)
    profile = ApplicantProfile.load(profile_with(tmp_path))

    with FakeJobServer(ARC_FORM) as fake:
        lines = hold_until(fake, profile, lambda lines: "you submitted it" in lines[-1], force=True,
                           with_adapters={"applied_before": AppliedTo()})
        submissions = len(fake.submissions)

    assert seen["note"].startswith("WorkIt You already applied on 2026-10-28\nWorkIt keeps Submit blocked")
    assert (seen["sent before"], seen["sent after one press"]) == (0, 0)
    assert submissions == 1  # his, once he dismissed the note on purpose
    assert any(line.startswith("Arc Boat Company | ") and "ready to submit" in line for line in lines)


@pytest.mark.parametrize("outcome", [rehearsal.FAILED, rehearsal.SIGN_IN, "handoff"])
def test_a_page_apply_stopped_on_before_the_last_never_says_submit_is_yours(outcome):
    done = rehearsal.Rehearsed(Posting("p", "JPMorgan Chase", "Intern", "https://jpmc.fa.oraclecloud.com/x"), outcome,
                               "element is not editable")
    said = done.warning()
    assert said == (rehearsal.NOT_SIGNED_IN if outcome == rehearsal.SIGN_IN else rehearsal.NOT_LAST) and done.wrong()
    assert "element is not editable" not in said  # Apply's detail stays in its summary line, never on the page


def test_a_form_filled_to_its_last_page_keeps_its_plain_note():
    done = rehearsal.Rehearsed(Posting("p", "Acme", "Intern", "https://acme.example/x"), rehearsal.READY)
    assert (done.warning(), done.wrong()) == ("", False)


class StepsSite:
    """A job site whose form has two pages, each its own document, in a browser of its own: Ask Claude going
    back a step loads a new one. Each POST is kept in `posts`, and none is answered."""

    PAGES = {"/apply/1": '<a href="/apply/2">Back to page 2</a><p>Review your application</p>',
             "/apply/2": '<form method="post" action="/apply/2"><label>GPA <input id="gpa" name="gpa" value="3.9">'
                         '</label><button>Submit application</button></form>'}

    def __init__(self):
        self.posts = []

    @contextmanager
    def open(self, url: str, worker: int = 0):
        def serve(route):
            if route.request.method == "POST":
                self.posts.append(route.request.url)
                return route.fulfill(content_type="text/html", body="<p>Thank you for applying!</p>")
            path = route.request.url.split("example.com", 1)[1]
            route.fulfill(content_type="text/html", body=self.PAGES.get(path, "<p>Not found</p>"))
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            try:
                page = browser.new_page()
                page.context.route("**/*", serve)
                page.goto(url)
                yield page
            finally:
                browser.close()


class _Claude:
    """Ask Claude's drive, played: it goes back to page 2 (a new document), fixes the GPA and presses Enter."""

    def drive(self, page, **given):
        page.click("text=Back to page 2")
        page.wait_for_selector("#gpa")
        page.fill("#gpa", "3.7")
        page.press("#gpa", "Enter")  # Enter in a field sends its form
        page.wait_for_timeout(500)
        return Drive({"blocked": False, "why": "", "reply": "Fixed the GPA.", "changed": [], "couldnt": [],
                      "waiting": [], "ticked": [], "remember": [], "apply_bug": []}, 3, 1_000)


class _Asking:
    """The held page's Ask Claude: one message, acted on with apply.ask under the drive guard."""

    def __init__(self):
        self.items, self.done = [{"id": "ask-1", "message": "page 2's GPA is wrong, it's 3.7"}], []

    def open(self, page) -> None:
        pass

    def close(self) -> None:
        pass

    def asked(self) -> list[dict]:
        items, self.items = self.items, []
        return items

    def __call__(self, page, item: dict) -> None:
        from apply import ask
        from apply.submit_guard import DriveGuard

        reply = ask.ask(_Claude(), page, item["message"], [], ask.Form(Posting("p", "Acme", "Intern", page.url)), "",
                        guard=DriveGuard(page))
        self.done.append(reply)


def test_ask_claude_on_a_held_page_sends_nothing_from_a_page_it_loads():
    # A held page is lifted for Lisul. Ask Claude drives it again, and a page it loads (going back a step) must be
    # guarded too: Enter in a field there must not send the application (KAN-638).
    site, release, asking = StepsSite(), threading.Event(), _Asking()
    kept = rehearsal._Kept(site, 0)
    timer = threading.Timer(4, release.set)
    timer.daemon = True
    timer.start()

    with kept.open("https://jobs.example.com/apply/1"):
        kept.hold(release, ask=asking)

    assert asking.done, "the message was taken"
    assert site.posts == []


def test_a_held_form_is_on_the_open_forms_list_until_lisul_sends_it(monkeypatch, tmp_path):
    # KAN-719: a restart of the Mac lost every held form (2026-11-04 and 05). The list keeps each one as it goes.

    path = tmp_path / "open-forms.json"
    monkeypatch.setattr(batch, "PATH", path)
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    profile = ApplicantProfile.load(profile_with(tmp_path))
    with FakeJobServer(ARC_FORM) as fake:
        [done] = rehearse([ARC_URL], fake, profile_with(tmp_path))
        [kept] = batch.forms(path)
        assert (kept["link"], kept["status"], kept["job_system"], kept["worker"]) == (ARC_URL, "ready to submit",
                                                                                     "greenhouse", 0)
        assert kept["application_id"] == done.posting.id and kept["record"] == done.record

        lisul_on_the_held_page(monkeypatch, lambda n: ["Submit application"])
        hold_until(fake, profile, lambda lines: "you submitted it" in lines[-1], submitted_to=InMemoryTracker())
    assert batch.forms(path) == []  # it went in: nothing to bring back


class _Shows:
    """A page at `url` that shows `text` (get_by_text(...).first.is_visible(), as the confirmation checks read)."""

    def __init__(self, url: str, text: str = ""):
        self.url, self.text = url, text

    def get_by_text(self, pattern):
        shown = bool(pattern.search(self.text))
        return type("Found", (), {"first": type("First", (), {"is_visible": lambda self: shown})()})()


def test_an_eightfold_page_claude_fill_filled_is_confirmed_by_eightfolds_own_check():
    """Microsoft's form is Claude fill's ("other"), but its page is Eightfold's (KAN-771)."""
    from apply.rehearsal import _confirmed, _eightfold
    done = _Shows("https://apply.careers.microsoft.com/careers/job/1970393557037859", "Application Submitted Congrats!")
    assert _eightfold(done) and _confirmed(done, "other")
    assert not _confirmed(_Shows(done.url, "Submit application"), "other")
    assert not _eightfold(_Shows("https://jobs.example.com/acme/1", "Application Submitted"))


def test_a_rehearsal_never_resets_a_password_of_an_account_lisul_made(monkeypatch):
    # KAN-878's review: Create Account's "already exists" pressed Forgot your password? in a rehearsal (a reopened
    # form's too, now that it signs in), and changed the password of the account Lisul uses.
    monkeypatch.setitem(FILLERS, "workday", NeverSubmittingWorkday)
    world = World()
    with FakeWorkdayServer(CACI_FORM, keychain=world.keychain, mailbox=world.mailbox,
                           accounts={(CACI, "test.person@example.com"): "Made-By-Hand1!"}) as server:
        [done] = rehearse([CACI_URL], server, world.profile, keychain=world.keychain, mailbox=world.mailbox)
    assert done.outcome == rehearsal.SIGN_IN and "A rehearsal resets no password" in done.why, done.why
    assert server.resets == [] and world.keychain.password(CACI) is None


# Stop applying and Remove in the student's window (KAN-874).

class StoppingBoard(RecordingBoard):
    """The run's board, which the rehearsal hands its stop and remove; `then(stop, remove)` presses them."""

    def __init__(self, then: Callable[[Callable[[], None], Callable[[str], bool]], None]):
        super().__init__()
        self._then, self._stop = then, None

    def stopping(self, stop: Callable[[], None]) -> None:
        self._stop = stop

    def removing(self, remove: Callable[[str], bool]) -> None:
        self.removed = []
        self._then(self._stop, lambda link: self.removed.append(remove(link)) or self.removed[-1])


def test_a_removed_job_leaves_waiting_to_start_and_never_runs(monkeypatch, tmp_path):
    """Fault: a job the student removed still opens, or still counts as waiting to start."""
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    later = ARC_URL + ("&" if "?" in ARC_URL else "?") + "copy=2"  # another Posting of the same form
    board = StoppingBoard(lambda stop, remove: (remove(later), remove(later)))
    lines = []
    with FakeJobServer(ARC_FORM) as fake:
        done = rehearsal.rehearse([ARC_URL, later], adapters(fake, board=board), ApplicantProfile.load(profile_with(tmp_path)),
                                  1, keep_open=False, out=lines.append)
        opened = len(fake.workers)

    assert board.removed == [True, False]  # gone the first time: nothing left to remove after
    assert [d.posting.url for d in done] == [ARC_URL]
    assert lines[0] == f"{later} | removed: it won't run" and len(lines) == 2
    assert opened == 1  # the removed job's page never opened
    waiting = [run for run in board.runs if "waiting" in run]
    assert waiting[0]["waiting"] == [ARC_URL, later] and waiting[-1]["waiting"] == []
    assert [run["queued"] for run in board.runs if "queued" in run][-1] == 0
    assert 1 not in board.captions  # no tile ever filled it


def test_stop_applying_ends_the_run_with_nothing_submitted_and_no_waiting_job_started(monkeypatch, tmp_path):
    """Fault: Stop leaves the run going till Ctrl-C, starts the job that waited, submits a form, or skips on_done."""
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    later = ARC_URL + ("&" if "?" in ARC_URL else "?") + "copy=2"

    class Board(StoppingBoard):
        def update(self, worker: int, **caption: object) -> None:
            super().update(worker, **caption)
            if caption.get("status") == "filling" and self._stop:  # the student presses Stop mid-fill
                self._stop()

    board, lines, done = Board(lambda stop, remove: None), [], []
    watchdog = threading.Timer(120, _thread.interrupt_main)  # a run Stop never ends fails, never hangs
    watchdog.start()
    try:
        with FakeJobServer(ARC_FORM) as fake:
            rehearsal.rehearse([ARC_URL, later], adapters(fake, board=board), ApplicantProfile.load(profile_with(tmp_path)),
                               1, keep_open=True, out=lines.append, on_done=lambda: done.append(True))
            opened, submissions = len(fake.workers), fake.submissions
    finally:
        watchdog.cancel()

    assert submissions == [] and opened == 1  # the waiting job never started
    assert lines[-1] == rehearsal.STOPPED_APPLYING
    assert [run["waiting"] for run in board.runs if "waiting" in run][-1] == []
    assert done == [True]  # what the run's ended jobs left to do (a Repair they filed) still runs, once


def test_stop_new_ones_only_keeps_the_filled_form_held_and_starts_no_waiting_job(monkeypatch, tmp_path):
    """Fault: Stop new ones only closes a held form, or still starts the job that waited."""
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    later = ARC_URL + ("&" if "?" in ARC_URL else "?") + "copy=2"
    held, seen, later_stop = [], [], []

    class Board(StoppingBoard):
        def update(self, worker: int, **caption: object) -> None:
            super().update(worker, **caption)
            if caption.get("status") == "filling" and not held:
                self._stop(new_only=True)  # the student presses Stop new ones only mid-fill
            if caption.get("again") and not held:  # the form is held for them: a second later they stop the run
                held.append(worker)
                later_stop.append(threading.Timer(1.0, lambda: (seen.append(self.captions[worker].get("again")), self._stop())))
                later_stop[0].start()

    board, lines = Board(lambda stop, remove: None), []
    watchdog = threading.Timer(120, _thread.interrupt_main)
    watchdog.start()
    try:
        with FakeJobServer(ARC_FORM) as fake:
            rehearsal.rehearse([ARC_URL, later], adapters(fake, board=board), ApplicantProfile.load(profile_with(tmp_path)),
                               1, keep_open=True, out=lines.append)
            opened, submissions = len(fake.workers), fake.submissions
    finally:
        watchdog.cancel()

    later_stop[0].join(5)
    assert held == [0]  # the form filled under way was held for the student after Stop new ones only
    assert seen == [True]  # and a second later it was still held, until the student stopped the run
    assert submissions == [] and opened == 1  # the waiting job never started
    assert rehearsal.STOPPED_NEW in lines and lines[-1] == rehearsal.STOPPED_APPLYING


def test_no_more_forms_open_than_the_cap_until_the_student_finishes_one(monkeypatch, tmp_path):
    """Fault: every job opens its own window while forms wait on the student, and a long run slows the computer to
    a halt (live, 2026-11-26)."""
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    monkeypatch.setattr(rehearsal, "OPEN_FORMS", 0)  # with one Worker: one form open at once
    later = ARC_URL + ("&" if "?" in ARC_URL else "?") + "copy=2"
    servers, held_at, opened_while_held = [], {}, []

    class Board(RecordingBoard):
        def let_go_asked(self, worker: int) -> bool:  # each held form, let go a second after it is held
            if not self.captions.get(worker, {}).get("again"):
                return False
            since = held_at.setdefault(worker, time.monotonic())
            if time.monotonic() - since < 1.0:
                return False
            if len(held_at) == 1:
                opened_while_held.append(len(servers[0].workers))
            return True

    board = Board()
    watchdog = threading.Timer(120, _thread.interrupt_main)
    watchdog.start()
    try:
        with FakeJobServer(ARC_FORM) as fake:
            servers.append(fake)
            rehearsal.rehearse([ARC_URL, later], adapters(fake, board=board), ApplicantProfile.load(profile_with(tmp_path)),
                               1, keep_open=True, out=lambda line: None)
            opened, submissions = len(fake.workers), fake.submissions
    finally:
        watchdog.cancel()

    assert opened_while_held == [1]  # a second after the first was held, the second job still hadn't opened
    assert opened == 2 and len(held_at) == 2  # once it was let go, the second opened and was held in turn
    assert submissions == []
    assert {"open_forms": 1} in board.runs  # OPEN_FORMS waiting, plus the one Worker's


def test_a_form_the_student_submits_frees_its_slot_while_its_tab_stays_open(monkeypatch, tmp_path):
    """Fault: a submitted form's thank-you tab keeps its slot, so once OPEN_FORMS forms are sent the run waits for
    ever with jobs queued and nothing filling (live, 2026-11-26)."""
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    monkeypatch.setattr(rehearsal, "OPEN_FORMS", 0)  # with one Worker: one form open at once
    monkeypatch.setattr(rehearsal, "CLOSE_AFTER_S", 600)  # its thank-you tab stays open
    lisul_on_the_held_page(monkeypatch, lambda n: ["Submit application"] if n == 1 else [])
    later = ARC_URL + ("&" if "?" in ARC_URL else "?") + "copy=2"
    sent_at, second_held_while_first_open, first_gone = {}, [], []

    class Board(RecordingBoard):
        def let_go_asked(self, worker: int) -> bool:
            if worker == 1 and self.captions.get(1, {}).get("again"):  # the second form opened and was held
                second_held_while_first_open.append(not first_gone)
                return True
            if worker == 0 and self.captions.get(0, {}).get("status") == "submitted":  # its tab closed by hand
                since = sent_at.setdefault(0, time.monotonic())
                if second_held_while_first_open or time.monotonic() - since > 5:
                    first_gone.append(True)
                    return True
            return False

    board = Board()
    watchdog = threading.Timer(120, _thread.interrupt_main)
    watchdog.start()
    try:
        with FakeJobServer(ARC_FORM) as fake:
            rehearsal.rehearse([ARC_URL, later], adapters(fake, board=board), ApplicantProfile.load(profile_with(tmp_path)),
                               1, keep_open=True, out=lambda line: None, submitted_to=InMemoryTracker())
            submissions = fake.submissions
    finally:
        watchdog.cancel()

    assert len(submissions) == 1  # the student's, from the first held page
    assert second_held_while_first_open == [True]  # the second form opened while the first's tab was still open


def test_a_submit_the_job_system_never_confirms_frees_its_slot_while_its_handoff_stays(monkeypatch, tmp_path):
    """Fault: each form Apply pressed Submit on but the job site never confirmed kept its slot as a handoff, so five of
    them stalled the run with jobs queued and nothing filling (live, 2026-11-26)."""
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    monkeypatch.setattr(rehearsal, "OPEN_FORMS", 0)  # with one Worker: one form open at once
    monkeypatch.setattr(rehearsal, "_confirmed", lambda page, job_system: False)
    monkeypatch.setattr(rehearsal, "CONFIRM_S", 1)
    later = ARC_URL + ("&" if "?" in ARC_URL else "?") + "copy=2"
    approved, second_held_while_first_handed_off = [], []

    class Board(RecordingBoard):
        def submit_asked(self, worker: int) -> bool:  # the first form is approved once
            if worker == 0 and self.captions.get(0, {}).get("again") and not approved:
                approved.append(worker)
                return True
            return False

        def let_go_asked(self, worker: int) -> bool:
            if worker == 1 and self.captions.get(1, {}).get("again"):  # the second form opened and was held
                second_held_while_first_handed_off.append(self.captions[0].get("again") is True)
                return True
            return worker == 0 and bool(second_held_while_first_handed_off)

    board = Board()
    watchdog = threading.Timer(120, _thread.interrupt_main)
    watchdog.start()
    try:
        with FakeJobServer(ARC_FORM) as fake:
            rehearsal.rehearse([ARC_URL, later], adapters(fake, board=board), ApplicantProfile.load(profile_with(tmp_path)),
                               1, keep_open=True, out=lambda line: None)
    finally:
        watchdog.cancel()

    assert board.captions[0]["why"] == rehearsal.UNCONFIRMED
    assert second_held_while_first_handed_off == [True]  # the second opened while the first's handoff was held


def test_not_applying_to_a_held_form_lets_its_page_go_unsubmitted_and_the_run_ends(monkeypatch, tmp_path):
    """Fault: Not applying to this one leaves the page held (the run never ends), or submits it."""
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    asked = []

    class Board(RecordingBoard):
        def let_go_asked(self, worker: int) -> bool:
            if self.captions.get(worker, {}).get("again") and not asked:  # held: the student presses it once
                asked.append(worker)
                return True
            return False

    board, lines = Board(), []
    watchdog = threading.Timer(120, _thread.interrupt_main)
    watchdog.start()
    try:
        with FakeJobServer(ARC_FORM) as fake:
            rehearsal.rehearse([ARC_URL], adapters(fake, board=board), ApplicantProfile.load(profile_with(tmp_path)),
                               1, keep_open=True, out=lines.append)
            submissions = fake.submissions
    finally:
        watchdog.cancel()

    assert asked == [0] and board.captions[0]["again"] is False  # held, then let go: held no more
    assert submissions == [] and rehearsal.STOPPED_APPLYING not in lines


def test_a_posting_sent_in_again_by_another_link_joins_the_run_no_more(monkeypatch, tmp_path):
    """Fault: a Greenhouse job sent in by its board link, then by its embed link (one token), was queued twice."""
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    took = []

    class Board(RecordingBoard):
        def taking(self, into):
            self.into = into

        def let_go_asked(self, worker: int) -> bool:  # held: the same job comes in again, then it is let go
            if not self.captions.get(worker, {}).get("again"):
                return False
            if not took:
                took.append(self.into(ARC_URL.replace("arcboatcompany/jobs/", "embed/job_app?for=arcboatcompany&token="),
                                      0, running=False))
            return True

    board = Board()
    watchdog = threading.Timer(120, _thread.interrupt_main)
    watchdog.start()
    try:
        with FakeJobServer(ARC_FORM) as fake:
            rehearsal.rehearse([ARC_URL], adapters(fake, board=board), ApplicantProfile.load(profile_with(tmp_path)),
                               1, keep_open=True, out=lambda line: None)
    finally:
        watchdog.cancel()

    assert took == [{"tile": 0, "worker": 0, "already": True}]
    assert list(board.captions) == [0]  # no second tile


def test_approve_and_submit_presses_the_held_forms_submit_once_and_waits_for_the_confirmation(monkeypatch, tmp_path):
    """ADR 0006. Fault: Approve and submit leaves the form unsent, presses Submit twice, or calls it submitted before
    the job system confirms it."""
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    asked = []

    class Board(RecordingBoard):
        def submit_asked(self, worker: int) -> bool:  # held: the student approves it, and presses again after
            if self.captions.get(worker, {}).get("again") and len(asked) < 2:
                asked.append(worker)
                return True
            return False

    board, lines = Board(), []
    watchdog = threading.Timer(120, _thread.interrupt_main)
    watchdog.start()
    try:
        with FakeJobServer(ARC_FORM) as fake:
            rehearsal.rehearse([ARC_URL], adapters(fake, board=board), ApplicantProfile.load(profile_with(tmp_path)),
                               1, keep_open=True, out=lines.append)
            submissions = fake.submissions
    finally:
        watchdog.cancel()

    assert len(submissions) == 1  # one press: the second approve finds it pressed already
    assert board.captions[0]["status"] == "submitted"
    assert board.captions[0]["submit_said"] == rehearsal.PRESSED_ALREADY


def test_an_approved_submit_whose_click_never_answered_counts_as_pressed_and_is_confirmed(monkeypatch, tmp_path):
    """Fault: a Submit that sends the page away (Lever's whole-page post) ends the click with an error, so Apply
    says it found no Submit button, never watches the job site's confirmation, and the card never shows it applied."""
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    real_press, asked = send_button.press, []

    def press_lost(page) -> str:  # the press lands, but its reply is lost to the page it sent away
        raise send_button.Unsure(real_press(page))
    monkeypatch.setattr(send_button, "press", press_lost)

    class Board(RecordingBoard):
        def submit_asked(self, worker: int) -> bool:
            if self.captions.get(worker, {}).get("again") and not asked:
                asked.append(worker)
                return True
            return False

    board = Board()
    watchdog = threading.Timer(120, _thread.interrupt_main)
    watchdog.start()
    try:
        with FakeJobServer(ARC_FORM) as fake:
            rehearsal.rehearse([ARC_URL], adapters(fake, board=board), ApplicantProfile.load(profile_with(tmp_path)),
                               1, keep_open=True, out=lambda line: None)
            submissions = fake.submissions
    finally:
        watchdog.cancel()

    assert len(submissions) == 1
    assert board.captions[0]["status"] == "submitted"
    assert board.captions[0].get("submit_said") != send_button.NONE


def test_an_approved_submit_the_job_system_never_confirms_is_a_handoff_never_pressed_again(monkeypatch, tmp_path):
    """ADR 0006. Fault: a press with no confirmation shows as submitted, or as held to be approved and sent again."""
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    monkeypatch.setattr(rehearsal, "_confirmed", lambda page, job_system: False)
    monkeypatch.setattr(rehearsal, "CONFIRM_S", 1)
    asked = []

    class Board(RecordingBoard):
        def submit_asked(self, worker: int) -> bool:
            caption = self.captions.get(worker, {})
            if caption.get("again") and caption.get("status") != "handoff":
                asked.append(worker)
                return True
            return False

        def let_go_asked(self, worker: int) -> bool:  # the student closes it once it is theirs
            return self.captions.get(worker, {}).get("status") == "handoff"

    board = Board()
    watchdog = threading.Timer(120, _thread.interrupt_main)
    watchdog.start()
    try:
        with FakeJobServer(ARC_FORM) as fake:
            rehearsal.rehearse([ARC_URL], adapters(fake, board=board), ApplicantProfile.load(profile_with(tmp_path)),
                               1, keep_open=True, out=lambda line: None)
            submissions = fake.submissions
    finally:
        watchdog.cancel()

    assert len(submissions) == 1  # pressed once; each approve after found it pressed already
    assert board.captions[0]["why"] == rehearsal.UNCONFIRMED
    assert board.captions[0]["submit_said"] == ""


def test_an_approved_submit_that_left_the_form_where_it_was_is_handed_over_as_unsent(monkeypatch, tmp_path):
    """Fault: Lever's hCaptcha held Apply's press back (Palantir, Veeva, live 2026-11-27): the same page, the form
    still on it, no email. Apply said it may have gone in and marked it sent, so it was never sent at all."""
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    monkeypatch.setattr(rehearsal, "_confirmed", lambda page, job_system: False)
    monkeypatch.setattr(rehearsal, "CONFIRM_S", 1)
    pressed_on = []
    monkeypatch.setitem(rehearsal.NEVER_SENT, "greenhouse",
                        (lambda page: pressed_on.append(1) or 1.0, lambda page, before: before == 1.0))
    noted = []
    real_note = rehearsal.batch.note
    monkeypatch.setattr(rehearsal.batch, "note", lambda url, **kw: (noted.append(kw.get("status")), real_note(url, **kw)))

    class Board(RecordingBoard):
        def submit_asked(self, worker: int) -> bool:
            caption = self.captions.get(worker, {})
            return bool(caption.get("again")) and caption.get("status") != "handoff" and not pressed_on

        def let_go_asked(self, worker: int) -> bool:
            return self.captions.get(worker, {}).get("status") == "handoff"

    board = Board()
    watchdog = threading.Timer(120, _thread.interrupt_main)
    watchdog.start()
    try:
        with FakeJobServer(ARC_FORM) as fake:
            rehearsal.rehearse([ARC_URL], adapters(fake, board=board), ApplicantProfile.load(profile_with(tmp_path)),
                               1, keep_open=True, out=lambda line: None)
    finally:
        watchdog.cancel()

    assert pressed_on == [1]
    assert board.captions[0]["why"] == rehearsal.NOT_SENT
    assert rehearsal.batch.SENT not in noted  # nothing went in: never kept from being sent again


# Greenhouse's own check in the page, as Epic Games' form answered Apply's press (live, 2026-11-26): the field is
# marked invalid under a red message, nothing is sent, and the message goes once the field takes an answer.
REFUSES = r"""(name) => {
  const field = document.getElementById(name), said = document.createElement('p');
  said.id = name + '-error'; said.className = 'helper-text helper-text--error';
  said.textContent = 'Please accept the terms to proceed.';
  field.after(said);
  field.setAttribute('aria-invalid', 'true'); field.setAttribute('aria-describedby', said.id);
  field.value = '';
  field.addEventListener('input', () => { said.remove(); field.removeAttribute('aria-invalid'); }, {once: true});
}"""


def refused_presses(monkeypatch, refusals: int, field: str = "first_name") -> list[str]:
    """Approve and submit's press, refused in the page `refusals` times as Greenhouse refuses it (REFUSES on
    `field`, emptied), then pressed for real. Each press's words, in order."""
    real_press, presses = send_button.press, []

    def press(page) -> str:
        if len(presses) < refusals:
            page.evaluate(REFUSES, field)
            presses.append("refused")
            return "Submit application"
        presses.append(real_press(page))
        return presses[-1]
    monkeypatch.setattr(send_button, "press", press)
    monkeypatch.setattr(rehearsal, "HEAL_AFTER_S", 0)
    return presses


def approved_once(captions: dict, asked: list) -> Callable[[int], bool]:
    def submit_asked(worker: int) -> bool:
        if captions.get(worker, {}).get("again") and not asked:
            asked.append(worker)
            return True
        return False
    return submit_asked


def test_a_submit_the_form_refuses_is_fixed_from_the_plan_and_pressed_once_more(monkeypatch, tmp_path):
    """Fault: a press Greenhouse refused in the page (a field emptied, "Please accept the terms to proceed.") waits
    out CONFIRM_S and is handed over as maybe sent, though Apply could fill the field it named and send it."""
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    presses, asked = refused_presses(monkeypatch, 1), []

    class Board(RecordingBoard):
        def submit_asked(self, worker: int) -> bool:
            return approved_once(self.captions, asked)(worker)

    board = Board()
    watchdog = threading.Timer(120, _thread.interrupt_main)
    watchdog.start()
    try:
        with FakeJobServer(ARC_FORM) as fake:
            rehearsal.rehearse([ARC_URL], adapters(fake, board=board), ApplicantProfile.load(profile_with(tmp_path)),
                               1, keep_open=True, out=lambda line: None)
            submissions = fake.submissions
    finally:
        watchdog.cancel()

    assert presses == ["refused", "Submit application"]  # the field filled again, then one press more
    assert len(submissions) == 1 and submissions[0].application.get("first_name") == "Test"
    assert board.captions[0]["status"] == "submitted"


def test_a_submit_the_form_still_refuses_after_one_fix_is_handed_over_with_its_words(monkeypatch, tmp_path):
    """Fault: Apply presses a refused Submit again and again, or hands it over as maybe sent (marked sent, never to
    be brought back) without the page's own message."""
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    presses, asked = refused_presses(monkeypatch, 5), []

    class Board(RecordingBoard):
        def submit_asked(self, worker: int) -> bool:
            return approved_once(self.captions, asked)(worker)

        def let_go_asked(self, worker: int) -> bool:
            return self.captions.get(worker, {}).get("status") == "handoff"

    board = Board()
    watchdog = threading.Timer(120, _thread.interrupt_main)
    watchdog.start()
    try:
        with FakeJobServer(ARC_FORM) as fake:
            rehearsal.rehearse([ARC_URL], adapters(fake, board=board), ApplicantProfile.load(profile_with(tmp_path)),
                               1, keep_open=True, out=lambda line: None)
            submissions = fake.submissions
    finally:
        watchdog.cancel()

    assert presses == ["refused", "refused"]  # one press more, never a third
    assert submissions == []
    assert board.captions[0]["why"] == rehearsal.STILL_REFUSED.format(said="'Please accept the terms to proceed.'")


def test_a_refusal_about_no_question_of_the_form_is_handed_over_unpressed(monkeypatch, tmp_path):
    """Fault: a message Apply can't tie to a question it planned (a whole-form error, a field it never read) is
    "fixed" by a guess and pressed again, or handed over without the page's words."""
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    monkeypatch.setattr(rehearsal, "_confirmed", lambda page, job_system: False)
    presses, asked = [], []

    def press(page) -> str:
        page.evaluate("""() => document.body.insertAdjacentHTML('beforeend',
          '<div role="alert">Please review the form before you send it.</div>')""")
        presses.append("refused")
        return "Submit application"
    monkeypatch.setattr(send_button, "press", press)
    monkeypatch.setattr(rehearsal, "HEAL_AFTER_S", 0)

    class Board(RecordingBoard):
        def submit_asked(self, worker: int) -> bool:
            return approved_once(self.captions, asked)(worker)

        def let_go_asked(self, worker: int) -> bool:
            return self.captions.get(worker, {}).get("status") == "handoff"

    board = Board()
    watchdog = threading.Timer(120, _thread.interrupt_main)
    watchdog.start()
    try:
        with FakeJobServer(ARC_FORM) as fake:
            rehearsal.rehearse([ARC_URL], adapters(fake, board=board), ApplicantProfile.load(profile_with(tmp_path)),
                               1, keep_open=True, out=lambda line: None)
    finally:
        watchdog.cancel()

    assert presses == ["refused"]
    assert board.captions[0]["why"] == rehearsal.REFUSED.format(said="'Please review the form before you send it.'")


def test_a_confirmation_in_an_alert_after_an_approved_submit_is_sent_never_refused(monkeypatch, tmp_path):
    """Fault: Oracle's "Thank you for your job application." (BGC's, live 2026-11-27, and the confirmation email came)
    showed in an alert, matched no thanks, and was read as a field error: the card said the site refused it."""
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    monkeypatch.delitem(rehearsal.CONFIRMED, "greenhouse")  # read by THANKS, as Oracle's page is
    presses, asked = [], []

    def press(page) -> str:
        page.evaluate("""() => document.body.insertAdjacentHTML('beforeend',
          '<div role="alert" class="notification-error">Thank you for your job application.</div>')""")
        presses.append("sent")
        return "Submit"
    monkeypatch.setattr(send_button, "press", press)
    monkeypatch.setattr(rehearsal, "HEAL_AFTER_S", 0)

    class Board(RecordingBoard):
        def submit_asked(self, worker: int) -> bool:
            return approved_once(self.captions, asked)(worker)

    board = Board()
    watchdog = threading.Timer(120, _thread.interrupt_main)
    watchdog.start()
    try:
        with FakeJobServer(ARC_FORM) as fake:
            rehearsal.rehearse([ARC_URL], adapters(fake, board=board), ApplicantProfile.load(profile_with(tmp_path)),
                               1, keep_open=True, out=lambda line: None)
    finally:
        watchdog.cancel()

    assert presses == ["sent"]  # never pressed again
    assert board.captions[0]["status"] == "submitted", board.captions[0].get("why")


@pytest.mark.parametrize("said", ["Thank you for your job application.", "Thank you for your application!",
                                  "Thank you for applying."])
def test_a_job_sites_thanks_reads_as_confirmed(said):
    assert rehearsal.THANKS.search(said) and FILL_THANKS.search(said)


# Workable's answer to Apply's press (Digital Control, Infleqtion, live 2026-11-27): a toast in no field, with no role
# or error class, gone within seconds; no confirmation and no email followed.
TOAST = """(lines) => {
  const toast = document.createElement('div');
  toast.innerText = lines.join('\\n');
  document.body.append(toast);
  setTimeout(() => toast.remove(), 3000);
}"""
WORKABLE_TOAST = ["Something went wrong. We are working on this, please try again later."]
# Oracle's, once a second tile signed in to the same site (Honeywell, live 2026-11-27): it was read as no refusal,
# and the form was handed over as one that may have gone in.
ORACLE_OTHER_TAB = ["Your application couldn't be submitted.",
                    "You already created your profile in another browser tab. To resume your job application, you need "
                    "to confirm your identity."]


@pytest.mark.parametrize("lines, why", [(WORKABLE_TOAST, "SITE_REFUSED"), (ORACLE_OTHER_TAB, "OTHER_TAB_REFUSED")])
def test_a_site_error_toast_after_an_approved_submit_is_handed_over_as_not_sent(monkeypatch, tmp_path, lines, why):
    """Fault: Workable's "Something went wrong ... try again later" toast went before the form was read for errors,
    and the form was handed over as one that may have gone in (marked sent, never brought back), not as refused."""
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    monkeypatch.setattr(rehearsal, "_confirmed", lambda page, job_system: False)
    monkeypatch.setattr(rehearsal, "CONFIRM_S", 30)
    presses, asked, noted = [], [], []
    monkeypatch.setattr(batch, "note", lambda url, **fields: noted.append(fields))

    def press(page) -> str:
        page.evaluate(TOAST, lines)
        presses.append("refused")
        return "Submit application"
    monkeypatch.setattr(send_button, "press", press)

    class Board(RecordingBoard):
        def submit_asked(self, worker: int) -> bool:
            return approved_once(self.captions, asked)(worker)

        def let_go_asked(self, worker: int) -> bool:
            return self.captions.get(worker, {}).get("status") == "handoff"

    board = Board()
    watchdog = threading.Timer(120, _thread.interrupt_main)
    watchdog.start()
    try:
        with FakeJobServer(ARC_FORM) as fake:
            rehearsal.rehearse([ARC_URL], adapters(fake, board=board), ApplicantProfile.load(profile_with(tmp_path)),
                               1, keep_open=True, out=lambda line: None)
            submissions = fake.submissions
    finally:
        watchdog.cancel()

    assert presses == ["refused"] and submissions == []
    assert board.captions[0]["why"] == getattr(rehearsal, why).format(said=" ".join(lines))
    assert {"status": batch.SENT} not in noted  # nothing went in: never kept from being sent again


def test_a_code_step_after_an_approved_submit_is_asked_for_never_handed_over_as_unconfirmed(monkeypatch, tmp_path):
    """Fault: Greenhouse's security code step after Apply's press waits out CONFIRM_S and becomes the "may have gone
    in" Handoff, over the code the student is asked for."""
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    monkeypatch.setattr(rehearsal, "_confirmed", lambda page, job_system: False)
    monkeypatch.setattr(rehearsal, "CONFIRM_S", 1)
    asked, since = [], {}

    def press(page) -> str:  # Greenhouse's code step comes in place of the confirmation
        page.evaluate("""() => document.body.insertAdjacentHTML('beforeend',
          '<label for="security_code">Security code</label><input id="security_code" name="security_code">')""")
        return "Submit application"
    monkeypatch.setattr(send_button, "press", press)

    class Board(RecordingBoard):
        def submit_asked(self, worker: int) -> bool:
            return approved_once(self.captions, asked)(worker)

        def let_go_asked(self, worker: int) -> bool:  # well past CONFIRM_S, the student lets it go
            return bool(asked) and time.monotonic() - since.setdefault(0, time.monotonic()) > 4

    board = Board()
    watchdog = threading.Timer(120, _thread.interrupt_main)
    watchdog.start()
    try:
        with FakeJobServer(ARC_FORM) as fake:
            rehearsal.rehearse([ARC_URL], adapters(fake, board=board), ApplicantProfile.load(profile_with(tmp_path)),
                               1, keep_open=True, out=lambda line: None)
    finally:
        watchdog.cancel()

    assert asked == [0]
    assert board.captions[0].get("why") != rehearsal.UNCONFIRMED and board.captions[0].get("status") != "handoff"


def test_auto_submit_presses_a_clean_held_forms_submit_once_its_wait_is_over(monkeypatch, tmp_path):
    """ADR 0006. Fault: a form Auto-submit may send waits for an approval anyway, or goes before its countdown."""
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    monkeypatch.setattr(auto_submit, "on", lambda profile: True)
    monkeypatch.setattr(auto_submit, "why_not", lambda *args: "")
    monkeypatch.setattr(auto_submit, "WAIT_S", 1)
    monkeypatch.setattr(auto_submit, "desktop", lambda notifier: None)  # no real notification from a test
    board, notifier = RecordingBoard(), RecordingNotifier()
    watchdog = threading.Timer(120, _thread.interrupt_main)
    watchdog.start()
    try:
        with FakeJobServer(ARC_FORM) as fake:
            rehearsal.rehearse([ARC_URL], adapters(fake, board=board, notifier=notifier), ApplicantProfile.load(profile_with(tmp_path)),
                               1, keep_open=True, out=lambda line: None)
            submissions = fake.submissions
    finally:
        watchdog.cancel()

    assert len(submissions) == 1
    assert board.captions[0]["status"] == "submitted"
    assert board.captions[0]["auto_at"] is None
    assert [title for title, _ in notifier.sent] == [auto_submit.TITLE]  # told it was coming


def test_cancel_stops_auto_submit_and_the_form_waits_for_the_student(monkeypatch, tmp_path):
    """ADR 0006. Fault: Cancel in the window doesn't stop the press."""
    monkeypatch.setitem(FILLERS, "greenhouse", NeverSubmits(GreenhouseFiller()))
    monkeypatch.setattr(auto_submit, "on", lambda profile: True)
    monkeypatch.setattr(auto_submit, "why_not", lambda *args: "")
    monkeypatch.setattr(auto_submit, "WAIT_S", 1)
    monkeypatch.setattr(auto_submit, "desktop", lambda notifier: None)  # no real notification from a test
    seen = []

    class Board(RecordingBoard):
        def auto_cancel_asked(self, worker: int) -> bool:  # Cancel, as soon as the countdown shows
            return bool(self.captions.get(worker, {}).get("auto_at"))

        def let_go_asked(self, worker: int) -> bool:  # then, well past the wait, the student closes it
            if self.captions.get(worker, {}).get("auto_said") != auto_submit.CANCELLED:
                return False
            seen.append(time.monotonic())
            return time.monotonic() - seen[0] > 2.5

    board = Board()
    watchdog = threading.Timer(120, _thread.interrupt_main)
    watchdog.start()
    try:
        with FakeJobServer(ARC_FORM) as fake:
            rehearsal.rehearse([ARC_URL], adapters(fake, board=board), ApplicantProfile.load(profile_with(tmp_path)),
                               1, keep_open=True, out=lambda line: None)
            submissions = fake.submissions
    finally:
        watchdog.cancel()

    assert submissions == []
    assert board.captions[0]["auto_said"] == auto_submit.CANCELLED
