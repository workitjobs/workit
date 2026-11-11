"""The Filler for amazon.jobs: plain code through the Fill engine's Amazon Stepper (its src/amazon.ts), not Claude fill.

Amazon's application is one page of step cards, after Lisul's own Amazon sign-in in the Worker (Apply never types
there: the engine reports the sign-in as a gate, and this Filler hands it to him). The engine visits every step in
the progress list's order, the ones Amazon ticks from his old Amazon profile too, so their stale answers (a Minor, a
graduation date) are read and corrected. Each step is planned, filled, read again for a follow-up, then left by the
step's own Continue through the engine (`next`), which never presses "Submit application". After Continue the step's
saved answers are read back: what Amazon kept is what the Record shows (Review & submit showed picked dates a day
early).

A text box Amazon takes only from a person's typing (KAN-716) is typed again here with Playwright's own fill, which a
plain Worker sends as trusted input once KAN-716's worker extension is in; a field still refused goes to the Rescue
(Claude, for that field), else it is a FillError a rehearsal skips. A required attestation (the Acknowledgement) is
Lisul's: the fill stops on its step for him, as Workday's does (KAN-676). Submit is his too: `submit` hands off.
"""

import re

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from apply import fill_engine
from apply.accounts import Accounts
from apply.adapters import JobSite
from apply.model import (
    Answers,
    FillError,
    Handoff,
    MoreQuestions,
    Question,
    QuestionSet,
    Readback,
    one_line,
)

FOLLOW_UP_WAIT = 300  # ms for a follow-up question to show once its question is answered
REFUSED = "won't leave its"  # the engine's Handoff when Continue doesn't leave the step
TRUSTED = "KAN-716"  # the engine's FillError for a typed box Amazon didn't take
TITLE = "a.job-title"  # the application's header: "<role> (ID: <job>)"
GATES = {
    "sign-in": "Sign in to amazon.jobs in this window, then press Resume. Apply never types into Amazon's sign-in.",
    "ai-preference": "amazon.jobs asks how it may use your information (its AI preference). Choose yourself, then press Resume.",
}


def next_step(page: Page, step: str) -> str:
    """The step's own Continue, through the engine, which never clicks a button that would send: the step shown next."""
    try:
        return fill_engine.call(page, "next", "amazon", step)
    except Handoff as handoff:
        if "would send the application" not in str(handoff):
            raise
        raise Handoff(f"{handoff}. Apply didn't click it: check the form and submit it yourself.") from None


class AmazonFiller:
    """A Filler for one amazon.jobs Application. Built per Application with its Accounts (unused: the sign-in is
    Lisul's), and the Rescue that fills a field the engine can't."""

    def __init__(self, accounts: Accounts, rescue=None, **_options):
        self._accounts = accounts
        self._rescue = rescue
        self._state: dict = {}  # the engine's memory of this Application (the steps it visited)
        self._readback: Readback = {}
        self._known: QuestionSet = []
        self._his: tuple[str, set[str]] = ("", set())  # (step, fields) Lisul set before Resume: not filled again
        self._paused_step = ""
        self.paused: dict | None = None
        self.names: tuple[str, str] = ("Amazon", "")
        self.step = ""

    # --- The Filler ------------------------------------------------------------------

    def form_url(self, url: str) -> str:
        return (fill_engine.job_of(url) or {}).get("form") or url

    def question_set(self, url: str, site: JobSite) -> QuestionSet:
        with site.open(self.form_url(url)) as page:
            shown = self._shown(page)
            return shown["questions"]

    def fill(self, page: Page, questions: QuestionSet, answers: Answers) -> Readback:
        try:
            return self._fill_steps(page, questions, answers)
        except Handoff:
            self._read_pause(page)
            raise

    def submit(self, page: Page) -> None:
        raise Handoff("amazon.jobs's Submit application is yours: check Review & submit and press it yourself.")

    def resume_blocked(self, page: Page) -> str:
        try:
            on_form = bool(page.locator("#my-progress-menu").count())
        except Exception:
            on_form = False
        return "" if on_form else "The form isn't on amazon.jobs's application yet: sign in on the page, then press Resume"

    def signed_in(self, page: Page) -> bool:
        return not self.resume_blocked(page)

    def resumed(self, page: Page) -> dict:
        """The values on the step shown that Lisul changed before pressing Resume, by Question name: fill() leaves
        them as they are. Only a value other than the one the step showed at the pause is his (KAN-676)."""
        shown = self._shown(page)
        values = self._values(page, shown)
        at_pause = self.paused if self.paused is not None and self._paused_step == shown["step"] else None
        attests = fill_engine.attestations(shown["questions"]) if at_pause is None else set()
        kept = {name: value for name, value in values.items() if value not in (None, "", [])
                and (value != at_pause.get(name) if at_pause is not None else name not in attests)}
        self._his = (shown["step"], set(kept))
        if at_pause is None:
            self.paused = None
        return kept

    @property
    def shown_so_far(self) -> Readback:
        return dict(self._readback)

    @property
    def rescued(self) -> list[str]:
        return list(self._rescue.notes) if self._rescue else []

    # --- The steps -------------------------------------------------------------------

    def _fill_steps(self, page: Page, questions: QuestionSet, answers: Answers) -> Readback:
        known = {q.name for q in questions}
        self._known = list(questions)
        attests = {name for name in fill_engine.attestations(questions) if name not in answers}  # Lisul's to tick
        refilled: set[str] = set()
        while not (shown := self._shown(page))["review"] and not shown["sends"]:
            step, fields = shown["step"], shown["questions"]
            if new := [q for q in fields if q.name not in known]:
                raise MoreQuestions(new)
            kept = self._his[1] if step == self._his[0] else set()
            for q in fields:
                if q.name in answers and q.name not in kept:
                    self._put_or_rescue(page, q, answers[q.name])
            page.wait_for_timeout(FOLLOW_UP_WAIT)
            if any(q.name not in known for q in self._shown(page)["questions"]):
                continue  # an answer brought up a follow-up question
            if unticked := [q.label for q in fields if q.required and q.name in attests and q.name not in kept]:
                raise Handoff(fill_engine.tick_ask(unticked))
            answered = [q.name for q in fields if q.name in answers]
            try:
                next_step(page, step)
            except Handoff as refused:
                if REFUSED not in str(refused) or step in refilled:
                    raise
                refilled.add(step)  # filled once more, then refused for good
                continue
            # What Amazon kept, read off the step's closed card: the read-back after Continue.
            if answered:
                self._readback |= fill_engine.call(page, "readback", "amazon", [], answered, self._state)
        return dict(self._readback)

    def _shown(self, page: Page) -> dict:
        shown = self._kept(fill_engine.call(page, "readQuestions", "amazon", self._state))
        if gate := shown.get("gate"):
            raise Handoff(GATES.get(gate, "amazon.jobs shows a page before its application: it is yours."))
        shown["questions"] = fill_engine.question_set(shown["questions"])
        self.step = str(shown.get("step") or "")
        self._name(page)
        return shown

    def _name(self, page: Page) -> None:
        """The role, as the application's header names it."""
        try:
            header = page.locator(TITLE).first
            if header.count():
                title = re.sub(r"\s*\(ID:\s*\d+\)\s*$", "", one_line(header.inner_text()))
                if title:
                    self.names = ("Amazon", title)
        except Exception:
            pass  # unnamed: the Feed's or the Request's name stands

    def _kept(self, result: dict) -> dict:
        self._state = result.pop("state", self._state)
        return result

    def _values(self, page: Page, shown: dict) -> dict:
        names = [q.name for q in shown["questions"] if q.kind != "file"]
        return fill_engine.call(page, "readback", "amazon", [], names, self._state) if names else {}

    def _read_pause(self, page: Page) -> None:
        try:
            shown = self._shown(page)
            self._paused_step, self.paused = shown["step"], self._values(page, shown)
        except Exception:
            self._paused_step, self.paused = "", None

    def _put_or_rescue(self, page: Page, q: Question, value) -> None:
        try:
            self._fill(page, {q.name: value})
        except (FillError, PlaywrightTimeoutError) as error:
            if isinstance(error, FillError) and TRUSTED in str(error) and self._type_trusted(page, q, value):
                return
            if self._rescue and self._rescue.field(page, q.label, value, error):
                return
            if isinstance(error, FillError):
                raise
            raise FillError(f"{q.label}: the Fill engine didn't finish it in time ({one_line(str(error))[:200]})") from error

    def _fill(self, page: Page, answers: Answers) -> Readback:
        result = self._kept(fill_engine.call(page, "fill", "amazon", fill_engine.questions_arg(self._known),
                                             fill_engine.answers_arg(answers), self._state))
        if "moreQuestions" in result:
            raise MoreQuestions(fill_engine.question_set(result["moreQuestions"]))
        self._readback |= result["readback"]
        return result["readback"]

    def _type_trusted(self, page: Page, q: Question, value) -> bool:
        """Types a text answer with Playwright's own fill, trusted on a plain Worker (KAN-716), and leaves the box:
        whether the box then holds it."""
        box = page.get_by_role("textbox", name=re.compile("^" + re.escape(q.label)))
        if box.count() != 1:
            return False
        box.fill(str(value))
        box.evaluate("e => e.blur()")
        page.wait_for_timeout(FOLLOW_UP_WAIT)
        shown = fill_engine.call(page, "readback", "amazon", [], [q.name], self._state).get(q.name)
        if shown != str(value):
            return False
        self._readback[q.name] = shown
        return True
