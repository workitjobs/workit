"""Auto-submit's eligibility (ADR 0006): only a form that needs nobody goes by itself."""

from dataclasses import dataclass, field, replace
from datetime import date
from types import SimpleNamespace

from apply import auto_submit, build
from apply.model import Posting, Status

TODAY = date(2026, 11, 26)


class Profile:
    def __init__(self, **policies):
        self._policies = {"auto_submit": True, "target_companies": ["Stripe"]} | policies

    def policy(self, key):
        return self._policies.get(key)


@dataclass
class Done:
    posting: Posting
    outcome: str = "ready"
    problems: tuple = ()
    missing: tuple = ()
    legal: tuple = ()
    left_behind: tuple = ()
    history: tuple = ()
    form: object = None
    saved: object = None
    why: str = ""
    title: str = ""


@dataclass
class Tracker:
    submitted: list = field(default_factory=lambda: ["ashby"])
    accounts: list = field(default_factory=list)

    def rows(self):
        return [SimpleNamespace(status=Status.SUBMITTED, job_system=s) for s in self.submitted]

    def employer_accounts(self):
        return self.accounts


def done(**kw) -> Done:
    return Done(Posting(id="1", company="Notion", title="SWE", url="https://jobs.ashbyhq.com/notion/1"), **kw)


def why(d, tracker=None, profile=None):
    return auto_submit.why_not(d, "ready", profile or Profile(), tracker or Tracker(), TODAY)


def test_a_clean_form_on_a_known_job_system_can_go():
    assert why(done()) == ""


def test_anything_that_needs_a_person_keeps_it_for_the_student():
    """Fault: a flagged, essay, paused, target, code-asking, new-account or new-system form is sent unseen."""
    essay = SimpleNamespace(written=[SimpleNamespace(essay=object())])
    assert why(done(outcome="handoff")) == auto_submit.NOT_READY
    assert why(done(problems=("Pre-submit review: GPA",))) == auto_submit.FLAGGED
    assert why(done(missing=("Why us?",))) == auto_submit.FLAGGED
    assert why(done(legal=(("Sponsorship", "says no"),))) == auto_submit.FLAGGED
    assert why(done(form=essay)) == auto_submit.ESSAY
    assert why(done(history=("10:00 Paused: captcha",))) == auto_submit.PAUSED
    stripe = done()
    stripe.posting = replace(stripe.posting, company="Stripe")
    assert why(stripe) == auto_submit.TARGET
    gh = done()
    gh.posting = replace(gh.posting, url="https://job-boards.greenhouse.io/notion/jobs/1")
    assert why(gh, Tracker(submitted=["greenhouse"])) == auto_submit.CODE.format("greenhouse")
    made = Tracker(accounts=[SimpleNamespace(company="Notion", created=TODAY)])
    assert why(done(), made) == auto_submit.ACCOUNT
    assert why(done(), Tracker(submitted=["lever"])) == auto_submit.NEW_SYSTEM.format("ashby")
    assert why(done(left_behind=(("GPA", "3.9"),))) == auto_submit.FLAGGED
    assert why(done(why="calibration run: 3 of 10 held")) == auto_submit.HELD
    assert why(done(saved=SimpleNamespace(essays="Why Notion? (cover letter file)"))) == auto_submit.ESSAY
    nameless = done()
    nameless.posting = replace(nameless.posting, company="")
    assert why(nameless) == auto_submit.NO_COMPANY
    other = done()
    other.posting = replace(other.posting, url="https://careers.example.com/jobs/1")
    assert why(other, Tracker(submitted=["other"])) == auto_submit.NEW_SYSTEM.format("other")


def test_an_account_made_on_an_earlier_day_doesnt_hold_it():
    before = Tracker(accounts=[SimpleNamespace(company="Notion", created=date(2026, 11, 1))])
    assert why(done(), before) == ""


def test_it_is_off_unless_the_policy_says_true_and_never_in_the_student_build(monkeypatch):
    assert auto_submit.on(Profile()) is True
    assert auto_submit.on(Profile(auto_submit=False)) is False
    assert auto_submit.on(Profile(auto_submit="yes")) is False
    monkeypatch.setattr(build, "STUDENT", True)
    assert auto_submit.on(Profile()) is False

