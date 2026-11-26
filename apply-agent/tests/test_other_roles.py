"""Other roles here: "Are you applying to other internships at <company>?" is
answered in code from the Tracker and the job board, never asked of the student
and never kept beyond its own company (apply.other_roles; Strava, 2026-11-26).
No browser, no network: the board is a stand-in site."""

import json

from fakes import FakeClaude
from test_claude_answers import MICROMOUSE, PROJECT, ResearchForm, run_all, sent_answer

from apply import home, other_roles
from apply.answer_bank import AnswerBank
from apply.model import Posting, Question, Status
from apply.profile import ApplicantProfile
from apply.tracker import TRACKER, FileTracker, Row

BOARD = "https://api.ashbyhq.com/posting-api/job-board/acme"
SERVER = "https://jobs.ashbyhq.com/acme/11111111-1111-4111-8111-111111111111"
MOBILE = "https://jobs.ashbyhq.com/acme/22222222-2222-4222-8222-222222222222"
DATA = "https://jobs.ashbyhq.com/acme/33333333-3333-4333-8333-333333333333"
POSTING = Posting("request-1", "Acme", "Software Engineering Intern, Server", f"{SERVER}/application")
OTHERS = Question("o", "Are you applying to any Acme internship besides this one? If so, which ones and why?", "textarea", True)


class Site:
    """Acme's Ashby board, and nothing else."""

    def __init__(self, jobs: list[dict] | None = None):
        self.jobs = jobs

    def fetch(self, url, body=None):
        if url != BOARD or self.jobs is None:
            raise OSError(f"no page at {url}")
        return json.dumps({"jobs": self.jobs}).encode()


BOARD_JOBS = [
    {"title": "Software Engineering Intern, Server", "jobUrl": SERVER, "descriptionPlain": "Go and PostgreSQL."},
    {"title": "Software Engineering Intern, iOS", "jobUrl": MOBILE, "descriptionPlain": "Swift and SwiftUI."},
    {"title": "Data Science Intern", "jobUrl": DATA, "descriptionPlain": "Python, SQL and dashboards."},
    {"title": "Hidden Intern", "jobUrl": "https://jobs.ashbyhq.com/acme/x", "isListed": False},
]


def profile(tmp_path, **facts) -> ApplicantProfile:
    return ApplicantProfile({"experience_facts": facts}, tmp_path, {})


def track(*rows: tuple[str, str, str, Status], requests: tuple[str, ...] = ()) -> None:
    tracker = FileTracker(TRACKER)
    for n, (company, role, url, status) in enumerate(rows):
        tracker.add(Row(f"a{n}", company, role, url, "ashby", status))
    for url in requests:
        tracker.add_request(url)


def test_the_question_is_told_apart_from_one_about_other_companies_or_jobs_anywhere():
    # Fault: a question about other employers (or about no company) answered as if it asked of this one.
    def ask(label):
        return other_roles.asks(Question("q", label, "textarea"), "Strava")
    assert ask("Are you applying for more than one internship at Strava? If so, why?")
    assert ask("Are you applying to any Strava internship besides Software Engineering Intern, Server, "
               "User Lifecycle, and if so, which ones and why?")
    assert ask("Is this the only role you are applying to with us?")
    assert not ask("Are you currently interviewing with other companies?")
    assert not ask("Are you applying for other jobs?")
    assert not ask("Why do you want to intern at Strava?")
    assert not ask("Have you applied to other positions within the last year?")


def test_no_other_application_is_a_plain_no_with_a_reason_from_his_skills(tmp_path):
    # Fault: "No" given without the role, or a why sentence from words his profile doesn't hold.
    said = other_roles.answer(OTHERS, POSTING, [], [], profile(tmp_path, skills=["Go", "Rust"]),
                              "You will write Go services.")
    assert said == ("No, Software Engineering Intern, Server is the only Acme internship I'm applying to. "
                    "It lists Go, which I have worked with.")
    assert other_roles.answer(OTHERS, POSTING, [], [], profile(tmp_path), "") == (
        "No, Software Engineering Intern, Server is the only Acme internship I'm applying to.")


def test_his_other_applications_there_are_named_from_the_tracker_and_the_board(tmp_path):
    # Fault: an application at another company, a failed one or this one named; a queued Request not named.
    track(("Acme", "Data Science Intern", DATA, Status.SUBMITTED),
          ("Acme", "Hardware Intern", "https://jobs.ashbyhq.com/acme/44444444-4444-4444-8444-444444444444", Status.FAILED),
          ("Acme", POSTING.title, SERVER, Status.HELD),  # this posting, by its link
          ("Beta", "Beta Intern", "https://jobs.lever.co/beta/2", Status.SUBMITTED),
          requests=(MOBILE,))
    board = other_roles.openings(POSTING, Site(BOARD_JOBS))
    assert [o.title for o in board] == [j["title"] for j in BOARD_JOBS[:3]]

    found = other_roles.others(POSTING, board)

    assert [(o.title, o.applied) for o in found] == [("Data Science Intern", True), ("Software Engineering Intern, iOS", False)]
    said = other_roles.answer(OTHERS, POSTING, found, board,
                              profile(tmp_path, skills=["Python", "SQL"], role_interests=["iOS/Mobile"]))
    assert said == ("Yes. I have also applied to Data Science Intern. I am applying to Software Engineering Intern, iOS. "
                    "Data Science Intern lists Python and SQL, which I have worked with. "
                    "Software Engineering Intern, iOS matches my interest in iOS work.")


def test_a_board_that_cant_be_read_leaves_the_tracker_to_say():
    # Fault: a board error stops the form, or a Request the board can't name is claimed by a made-up title.
    assert other_roles.openings(POSTING, Site(None)) == []
    assert other_roles.openings(Posting("p", "Acme", "Intern", "https://jobs.example.com/1"), Site(BOARD_JOBS)) == []


def test_a_yes_or_no_choice_picks_the_option_that_says_it_and_only_flips_it(tmp_path):
    # Fault: "Is this the only role" answered as if it asked about other roles, or "Have you applied" said Yes
    # for an application not yet sent.
    found = [other_roles.Other("Data Science Intern", True, DATA)]
    other = Question("c", "Have you applied to other roles at Acme?", "select", True, ("Yes", "No"))
    only = Question("c", "Is this the only role you are applying to at Acme?", "select", True, ("Yes", "No"))
    assert other_roles.answer(other, POSTING, found, [], profile(tmp_path)) == "Yes"
    assert other_roles.answer(only, POSTING, found, [], profile(tmp_path)) == "No"
    assert other_roles.answer(only, POSTING, [], [], profile(tmp_path)) == "Yes"
    queued = [other_roles.Other("Data Science Intern", False, DATA)]
    past = Question("c", "Have you previously applied to other roles at Acme?", "select", True, ("Yes", "No"))
    assert other_roles.answer(past, POSTING, queued, [], profile(tmp_path)) == "No"  # not sent yet
    applying = Question("c", "Are you applying to other roles at Acme?", "select", True, ("Yes", "No"))
    assert other_roles.answer(applying, POSTING, queued, [], profile(tmp_path)) == "Yes"
    # Typed, "the only role" is answered as asked too.
    typed = Question("t", only.label, "text", True)
    assert other_roles.answer(typed, POSTING, [], [], profile(tmp_path)).startswith("Yes, Software Engineering Intern")
    assert other_roles.answer(typed, POSTING, found, [], profile(tmp_path)) == (
        "No. I have also applied to Data Science Intern.")


def test_the_form_gets_the_answer_with_no_model_call_no_question_for_him_and_no_bank_entry(monkeypatch):
    # Fault: the question reaches Claude, Needs you or the Answer bank (Strava, 2026-11-26).
    asked = "Are you applying to any other Example Co internships? If so, which ones and why?"
    form = ResearchForm("Northwood Space")
    form.questions = form.questions + [Question("qo", asked, "textarea", True)]
    track(("Example Co", "Data Intern", "https://jobs.lever.co/example/abc", Status.SUBMITTED))
    claude, bank, story = FakeClaude(essays={PROJECT: MICROMOUSE}), AnswerBank(), home.STORY_BANK.read_text()

    [row] = run_all(monkeypatch, form, claude, ["Example Co"], bank=bank)

    assert row.status == "submitted", row.reason
    assert sent_answer(form, asked) == "Yes. I have also applied to Data Intern."
    # Only the Pre-submit review reads it, as it reads every answer: no call writes it.
    assert [call["kind"] for call in claude.kinds if asked in str(call)] == ["presubmit.review"]
    assert not any(e.question == asked for e in bank.entries())
    assert home.STORY_BANK.read_text() == story

