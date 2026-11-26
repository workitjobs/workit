"""The generic Filler (KAN-861, W2 step 2 of docs/desktop_application_auto_apply.md, D13): the Student build's
Filler for a job system with no Filler of its own. No model drives the browser: code reads the form and does every
click, and a model only picks.

- **Read.** apply.form_tree reads each control's role and name from the page's accessibility tree, with no model.
  A posting page with no field and one Apply button or link opens its form first (`_open_form`).
- **Fill, with plain code.** A text box takes its planned answer; a native select, radio group, checkbox or set of
  checkboxes takes the option the plan fitted to its options (the Fill engine's fit.ts, in its planner); a
  dropdown is opened and its option clicked; a search box is typed into and its listed choice clicked; a file is
  set (the résumé by apply.attach, any other through apply.upload_origin).
- **Pick, with a model, only when code can't.** A choice the page lists only as the fill opens or types (a search
  box, a dropdown read late, a two-level list's groups) is matched by its exact words, then by the Fill engine's
  `shows`; with none, one small question goes to WorkIt's Model route (`generic_fill.pick`: which of these options
  is the answer, about a hundred tokens), and code clicks the option it names.
- **Read back.** Every field is read back right after its fill. One that doesn't show its answer is a FillError
  that names it: the Worker drops it, and in the Student build it is a Needs-you item with its planned answer
  (KAN-855, docs/held-forms.md).
- **Hand over.** A page in a state the fill didn't expect (an error, a pop-up it can't close, a field that reset
  once filled), a widget the tree doesn't show (a drawing area, drag and drop), and a step whose end isn't clear
  (no Next and no button that sends) are each a Handoff: the student goes on in the Apply window.
- **Next.** Claude fill's NEXT and BACK patterns find the step's Next (apply.steps); plain code presses it through
  the guards (`press_step`). When two buttons could go on, `generic_fill.next` asks which goes on without sending.
  The step with a button that sends and no Next is the last: the fill stops there.

The Filler never submits: its `submit` refuses, and no button it presses may send (press_step's own check, the
rehearsal's guard and the drive guard on the page, KAN-666).
"""

import re
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

from playwright.sync_api import Page

from apply import captcha, description, fill_engine, form_tree, upload_origin
from apply.account_pages import SENDS
from apply.adapters import JobSite, SetupError, UsageLimitHit
from apply.attach import RESUME, attach_resume, clear_pop_up
from apply.form_tree import Field, locate, submits
from apply.model import (
    Answers,
    Captcha,
    FillError,
    Handoff,
    MoreQuestions,
    QuestionSet,
    Readback,
)
from apply.steps import BACK, FIELD_TEXT, NEXT, OPENS_MS, _owned_listbox, press_step
from apply.submit_guard import DriveGuard, drive_blocks

MAX_STEPS = 20  # a guard against a loop, as Claude fill's
MAX_CHOICES = 60  # the most options one model question lists; more is a Needs-you item
PAGE_SETTLES_MS = 5_000
# The button or link on a posting page that opens its form ("Apply for This Job", BambooHR's): its whole name.
OPENS = re.compile(r"^\W*(apply( now| online| here)?|apply (for|to) (this|the) (job|position|role|opening|internship)"
                   r"|start (your |an |my )?application|i'?m interested)\W*$", re.IGNORECASE)
# An alert whose words say the page refused something: an unexpected state, never one to fill past.
ERROR_WORDS = re.compile(r"\b(error|invalid|required|please (enter|select|provide|fix|correct)|must|failed|unable|"
                         r"couldn'?t|can ?not|cannot|went wrong|try again)\b", re.IGNORECASE)
CAPTCHA_CHALLENGE = ("A captcha's challenge covers the form, and Apply never touches a captcha. Do it on the form, "
                     "and the fill goes on")
CAPTCHA_BOX = "The form has a captcha (\"I'm not a robot\") to do before it can be sent. Do it on the form, and Apply goes on"
# Where the student does what Apply can't, in the Student build: the form's live view in the Apply window, which
# Fix here gives them (KAN-855). They never go to the Worker's own Chrome window, but for a captcha. Each Handoff here
# says what Apply saw, then this.
FIX_HERE = "press Fix here and {} on the form in this window"
FIX = FIX_HERE
NO_FIELDS = "Apply found no form fields on the page it can read. " + "To go on, " + FIX.format("fill it in")
NO_OPENER = ("The posting shows no form, and Apply found no one Apply button to open it ({}). To go on, "
             + FIX.format("open and fill the form"))
ALERT = "The form shows an error Apply didn't expect ({!r}). To go on, " + FIX.format("fix it")
POP_UP = "A pop-up covers the form ({!r}) and Apply couldn't close it. To go on, " + FIX.format("close it and fill the form")
RESET = ("{} went blank or changed after Apply filled it, so Apply stopped. To go on, "
         + FIX.format("check the page and fill it"))
UNREAD = ("Page {} has {} that Apply can't read or fill. To go on, " + FIX.format("fill it"))
UNCLEAR = ("Apply found no Next and no button that sends on page {}, so it can't tell where the form goes on. "
           "To go on, " + FIX.format("fill it"))
MANY_NEXT = ("Page {} has more than one button that could go on ({}), and none is clearly the form's Next. To go on, "
             + FIX.format("fill it"))
TOO_MANY_STEPS = f"Apply went through {MAX_STEPS} pages without reaching the form's last. To go on, " + FIX.format("fill it")
BLOCKED = ("The guard stopped a press that could have sent the form ({}). Nothing was sent. To go on, "
           + FIX.format("check the page"))
TO_TICK = "Page {}: {}"
SENDING_FORM = ("Page {1}'s {0!r} would submit a form that also holds the button that sends it, so Apply didn't press "
                "it. To go on, " + FIX.format("check the page and go on"))
NEVER_SUBMITS = "WorkIt Auto Apply never presses Submit"
# A part of the page no tree shows: a drawing area (a signature pad, a canvas date picker) or a drag and drop.
UNREADABLE = r"""() => {
  const big = (el) => { const r = el.getBoundingClientRect(); return r.width >= 120 && r.height >= 40; };
  const inForm = (el) => !!el.closest('form, [role=form], main');
  const canvas = [...document.querySelectorAll('canvas')].filter((el) => big(el) && inForm(el) && el.checkVisibility());
  const drag = [...document.querySelectorAll('[draggable=true]')].filter((el) => inForm(el) && el.checkVisibility());
  return canvas.length ? 'a drawing area (a signature, or a date picker drawn on a canvas)'
    : drag.length > 1 ? 'a list to put in order by drag and drop' : '';
}"""
# An opener's own link, to go to with no click: an http(s) link of the page's, else "" (a script's link is pressed).
OPENER_HREF = "el => (el.tagName === 'A' && /^https?:/.test(el.href) && !el.target) ? el.href : ''"
# Its link's origin, and the page's: a link to another site is never followed (the review of KAN-861: the Filler would
# then fill, and give files to, a site that isn't the posting's).
SAME_ORIGIN = "el => new URL(el.href, location.href).origin === location.origin"
# Whether a button sits in a form, or names one: its press could send that form.
IN_A_FORM = "el => !!(el.form || el.closest('form') || el.getAttribute('form'))"
# The words of each other button of the form a click on this element would submit, or [] when it submits none: a Next
# that submits the form its Submit is in could send it (a GET form's own submit handler, the review of KAN-861).
FORM_BUTTONS = r"""el => {
  const b = el.closest('button, input');
  const submits = !!b && !!b.form && (b.tagName === 'BUTTON'
    ? (b.getAttribute('type') || 'submit').toLowerCase() === 'submit' : /^(submit|image)$/i.test(b.type || ''));
  if (!submits) return [];
  return [...b.form.elements].filter((x) => x !== b && /^(BUTTON|INPUT)$/.test(x.tagName) && (x.tagName === 'BUTTON'
      || /^(submit|image|button)$/i.test(x.type || '')))
    .map((x) => [x.innerText, x.value, x.getAttribute('aria-label'), x.getAttribute('title'),
      // a name it takes from elsewhere, or from a picture: aria-labelledby, an image's alt, an icon's <title>
      ...(x.getAttribute('aria-labelledby') || '').split(/\s+/).filter(Boolean).map((id) => document.getElementById(id)?.textContent),
      ...[...x.querySelectorAll('img[alt], svg title')].map((i) => i.getAttribute('alt') || i.textContent)]
      .filter(Boolean).join(' '));
}"""
CHOSEN = "el => el.multiple ? [...el.selectedOptions].map((o) => o.text.trim()) : (el.selectedIndex >= 0 ? el.options[el.selectedIndex].text.trim() : '')"
FILE_NAMES = "el => [...(el.files || [])].map((f) => f.name)"

# One field's question to the model: the options' place in `options` that is the answer, or None. A Next's: the
# place in `buttons` of the one that goes on without sending, or None.
Pick = Callable[[str, list[str], str], int | None]
PickNext = Callable[[list[str]], int | None]


def picker(claude) -> tuple[Pick, PickNext]:
    """The two small questions, through WorkIt's Model route (`ask_kind`; the prompts are the server's,
    backend/app/apply_prompts/generic_fill.py). `claude` is the run's, as the applicant (apply.applicant.as_applicant),
    so the student's private values go as placeholders."""

    def pick(question: str, options: list[str], answer: str) -> int | None:
        said = claude.ask_kind("generic_fill.pick", {"question": question, "answer": answer, "options": options})
        return _place(said.get("choice"), len(options))

    def next_button(buttons: list[str]) -> int | None:
        said = claude.ask_kind("generic_fill.next", {"buttons": buttons})
        return _place(said.get("choice"), len(buttons))
    return pick, next_button


def _place(choice, count: int) -> int | None:
    return choice if isinstance(choice, int) and not isinstance(choice, bool) and 0 <= choice < count else None


class GenericFiller:
    """A Filler for one Application on a job system with no Filler of its own. Its form stays open from its Question
    set to its last step, so the Orchestrator runs it on OnePage."""

    def __init__(self, pick: Pick | None = None, next_button: PickNext | None = None, resume: Path | None = None,
                 sms_opt_in: bool = False, marketing_opt_in: bool = False, max_steps: int = MAX_STEPS):
        """`pick` and `next_button` are the model's two small questions (`picker`); without them, what code can't
        match is a Needs-you item, and two possible Nexts a Handoff. `resume` is for a pop-up that asks for it before
        the form can be used. The opt-ins are the student's policies: the drive guard refuses any other tick."""
        self._pick, self._next_button = pick, next_button
        self._resume = resume
        self._opt_ins = {"sms_opt_in": sms_opt_in, "marketing_opt_in": marketing_opt_in}
        self._max_steps = max_steps
        self._guard: DriveGuard | None = None
        self._fields: dict[str, Field] = {}  # each question the fill found, by its name
        self._found_at: dict[str, int] = {}  # the step each was found on
        self._named = 0
        self._steps = 0  # the steps gone past
        self._readback: Readback = {}  # what each field showed once filled, on every step
        self._put: dict[str, object] = {}  # the answer each field was filled with and showed
        self._failed: set[str] = set()  # the fields that didn't take their answer: the student's now
        self._alerts: set[str] = set()  # the alerts the page showed before Apply filled anything
        self._asked: tuple[dict[str, str], Answers] = ({}, {})
        self._attests: set[str] = set()  # the attestations and signatures: the student's own to tick (KAN-676)
        self.picked: list[tuple[str, str]] = []  # (label, option) of each choice the model picked, for the Record
        self.posting_text = ""
        self.names: tuple[str, str] = ("", "")

    # --- the Filler's shape (apply.fillers.Filler)

    def question_set(self, url: str, site: JobSite) -> QuestionSet:
        with site.open(url) as page, self._driving(page):  # its reads open dropdowns and close pop-ups: guarded
            self._settle(page)
            self._read_posting(page)
            self._clear(page)
            fields = form_tree.read(page)
            if not fields:
                self._open_form(page)
                self._clear(page)
                fields = form_tree.read(page)
            if not fields:
                raise Handoff(NO_FIELDS)
            self._read_posting(page)
            self._alerts = _alerts(page)
            return self._questions(fields)

    def fill(self, page: Page, questions: QuestionSet, answers: Answers) -> Readback:
        """Fill the step showing, read each field back, press its Next, and so on to the last step, the one with
        the button that sends. Called again after MoreQuestions or a FillError, it goes on from the step the page is
        on, with what is not yet on the form."""
        labels = {q.name: q.label for q in questions}
        self._asked = (labels, answers)
        self._attests = fill_engine.attestations(questions)
        with self._driving(page):
            return self._fill(page, labels, answers)

    def _fill(self, page: Page, labels: dict[str, str], answers: Answers) -> Readback:
        while True:
            self._clear(page)
            fields = form_tree.read(page, open_dropdowns=False)
            here = self._on_step(page, fields)  # raises MoreQuestions for a field no question names yet
            if self._resume_first(page, here, labels, answers):
                continue
            for name, field in here.items():
                if name in self._failed or name in self._put and self._put[name] == answers.get(name):
                    continue
                value = answers.get(name)
                if value is None or value == "" or value == []:
                    continue
                self._fill_one(page, name, labels.get(name, field.label), field, value)
            self._check_step(page, here)
            nxt = self._next(page)
            if nxt is None:  # the last step: it has the button that sends, which only the student presses
                if captcha.pending(page):
                    raise Captcha(CAPTCHA_BOX, page)
                return dict(self._readback)
            self._steps += 1
            if self._steps >= self._max_steps:
                raise Handoff(TOO_MANY_STEPS)
            if _submits_a_sending_form(page, nxt):
                raise Handoff(SENDING_FORM.format(nxt, self._steps))
            press_step(page, self._guard, nxt)
            self._guard.arm()  # press_step rests the guard once its press is done: driving again
            self._blocked()

    def submit(self, page) -> None:
        raise SetupError(NEVER_SUBMITS)

    def resumed(self, page: Page) -> dict:
        """The student pressed Resume after a Handoff: what they put in a field Apply had filled on this step is
        their answer, and the fill leaves it."""
        theirs = {}
        try:
            fields = form_tree.read(page, open_dropdowns=False)
        except Exception:
            return {}
        for name, field in self._match(fields).items():
            if name in self._put and field.shows not in ("", ()) and not _same(field.shows, self._put[name]):
                theirs[name] = list(field.shows) if isinstance(field.shows, tuple) else field.shows
                self._put[name] = self._readback[name] = theirs[name]
        self._failed -= set(theirs)
        return theirs

    @property
    def left_behind(self) -> list[tuple[str, object]]:
        """(label, answer) of each answer whose step went by before it came: the Worker holds the form for it."""
        labels, answers = self._asked
        return [(labels[name], value) for name, value in answers.items()
                if name in labels and value not in ("", None, []) and name in self._found_at
                and self._found_at[name] < self._steps and name not in self._put and name not in self._failed]

    @property
    def shown_so_far(self) -> Readback:
        return dict(self._readback)

    # --- reading

    def _settle(self, page: Page) -> None:
        try:
            page.wait_for_load_state("networkidle", timeout=PAGE_SETTLES_MS)
        except Exception:
            pass  # some pages never go quiet

    def _read_posting(self, page: Page) -> None:
        """The Posting's text and names off the open page, for the planner and the essays: a page that can't be read
        leaves them, and the Worker reads them another way."""
        try:
            self.posting_text = self.posting_text or description.from_page(page)
            if not all(self.names):
                company, title = description.names_on_page(page)
                self.names = (self.names[0] or company, self.names[1] or title)
        except Exception:
            pass

    def _questions(self, fields: list[Field]) -> QuestionSet:
        questions, by_name = form_tree.questions(fields, first=self._named + 1)
        self._named += len(fields)
        self._fields.update(by_name)
        self._found_at.update({name: self._steps for name in by_name})
        return questions

    def _match(self, fields: list[Field]) -> dict[str, Field]:
        """The fields read now that the fill knows, by their question's name: each as the Question set read it (its
        options, and how it fills), with what it shows now."""
        known = {field.key: name for name, field in self._fields.items()}
        return {known[f.key]: replace(self._fields[known[f.key]], shows=f.shows,
                                      controls=f.controls or self._fields[known[f.key]].controls)
                for f in fields if f.key in known}

    def _on_step(self, page: Page, fields: list[Field]) -> dict[str, Field]:
        """The known fields this step shows; a field no question names yet (the next step's, or one a pick showed)
        is read again with its dropdowns opened and raised as MoreQuestions, for the Worker to plan. A step with no
        field (a last page with only its Submit) has none: its Next, or its end, decides."""
        here = self._match(fields)
        if len(here) < len(fields):
            known = {f.key for f in here.values()}
            fresh = [f for f in form_tree.read(page) if f.key not in known and f.key not in
                     {field.key for field in self._fields.values()}]
            if fresh:
                raise MoreQuestions(self._questions(fresh))
        return here

    # --- filling

    def _guard_on(self, page: Page) -> None:
        if self._guard is None:
            self._guard = DriveGuard(page, **self._opt_ins)

    @contextmanager
    def _driving(self, page: Page):
        """The drive guard on and driving while code reads and fills (review of KAN-861): on a page the rehearsal
        left lifted too, every click that could send is blocked, and a captcha's frame takes none. It rests when the
        code stops, so the student's own clicks go through on the held page."""
        self._guard_on(page)
        self._guard.arm()
        try:
            yield
        finally:
            self._guard.rest()

    def _blocked(self) -> None:
        """Whatever the guards stopped while code pressed: a Handoff, since a press could have sent the form."""
        if self._guard is not None and (blocked := drive_blocks(self._guard.blocked())):
            self._guard.forget()
            raise Handoff(BLOCKED.format("; ".join(blocked)))

    def _resume_first(self, page: Page, here: dict[str, Field], labels: dict[str, str], answers: Answers) -> bool:
        """The résumé, attached by apply.attach before anything else (a form may parse it into its fields). True
        when that changed the step, so it is read again."""
        for name, field in here.items():
            value = answers.get(name)
            if field.how != "file" or not isinstance(value, Path) or name in self._put or name in self._failed:
                continue
            if not re.search(RESUME, labels.get(name, field.label), re.IGNORECASE):
                continue
            if attach_resume(page, value, self._guard):
                self._put[name] = value
                self._readback[name] = value.name
            else:
                self._failed.add(name)
                raise FillError(f"{_said(labels.get(name, field.label))}: the page didn't take the résumé")
            return True
        return False

    def _fill_one(self, page: Page, name: str, label: str, field: Field, value) -> None:
        """Fill one field and read it back. A field that doesn't show its answer is the student's: a FillError
        that names it."""
        try:
            put = self._put_value(page, label, field, value)
        except FillError:
            self._failed.add(name)
            raise
        except Exception as error:
            self._failed.add(name)
            raise FillError(f"{_said(label)}: Apply couldn't fill it ({type(error).__name__})") from error
        self._blocked()
        shown = self._read_back(page, field, put)
        self._readback[name] = shown
        if not fill_engine.shows(shown, put.name if isinstance(put, Path) else put):
            self._failed.add(name)
            if field.how == "text":  # no wrong answer left on the page: the student's box starts with the planned one
                try:
                    locate(page, field.role, field.name, field.nth).fill("")
                except Exception:
                    pass
            raise FillError(f"{_said(label)}: the page shows {shown!r} after Apply filled it")
        self._put[name] = value

    def _put_value(self, page: Page, label: str, field: Field, value):
        """Put `value` in `field` by plain code. Returns what the field should show once it has it."""
        how = field.how
        if how == "text":
            box = locate(page, field.role, field.name, field.nth)
            box.fill(str(value))
            box.blur()  # as a person leaves the box: the page's own checks of it run (its change, its blur)
            if not box.input_value(timeout=3_000).strip() and not re.search(r"[\r\n]", str(value)):
                # A masked box (a date's, BambooHR's) takes only keys: typed once more, key by key. Never a line
                # break: in a one-line box it is an Enter, which can send its form (KAN-716).
                box.click(timeout=5_000)
                box.press_sequentially(str(value), delay=20)
                box.blur()
            return str(value)
        if how == "native select":
            box = locate(page, field.role, field.name, field.nth)
            wanted = value if isinstance(value, list) else [value]
            chosen = [self._choose(label, list(field.options), str(v)) for v in wanted]
            if None in chosen:
                raise FillError(f"{_said(label)}: no option fits {value!r}")
            box.select_option(label=chosen if field.kind == "multi_select" else chosen[0])
            return chosen if field.kind == "multi_select" else chosen[0]
        if how == "radios":
            choice = self._choose(label, list(field.options), str(value))
            if choice is None:
                raise FillError(f"{_said(label)}: no option fits {value!r}")
            role, name, nth = field.controls[field.options.index(choice)]
            _check(label, locate(page, role, name, nth), True)
            return choice
        if how == "checkbox":
            yes = str(value).strip().lower() in ("yes", "true")
            _check(label, locate(page, field.role, field.name, field.nth), yes)
            return "Yes" if yes else "No"
        if how == "checkboxes":
            wanted = value if isinstance(value, list) else [v.strip() for v in str(value).split(";")]
            chosen = {self._choose(label, list(field.options), str(v)) for v in wanted} - {None}
            if not chosen:
                raise FillError(f"{_said(label)}: no option fits {value!r}")
            for option, (role, name, nth) in zip(field.options, field.controls):
                _check(label, locate(page, role, name, nth), option in chosen)
            return [o for o in field.options if o in chosen]
        if how == "file":
            if not isinstance(value, Path):
                raise FillError(f"{_said(label)}: the plan gave it no file")
            upload_origin.give(page.locator("input[type=file]").nth(field.nth), value)
            return value
        if how in ("dropdown", "search", "two-level"):
            return self._pick_in(page, label, field, value)
        raise FillError(f"{_said(label)}: Apply has no way to fill a {how}")

    def _pick_in(self, page: Page, label: str, field: Field, value) -> str:
        """A dropdown of the page's own making: opened (a search box: typed into), its listed choice found by code
        or picked by the model, and clicked. A two-level list's group is picked first, then its choice."""
        if isinstance(value, list):
            value = value[0] if value else ""
        answer = str(value)
        box = locate(page, field.role, field.name, field.nth)
        if field.role == "listbox":  # always open: its own options, clicked where they are
            choice = self._choose(label, list(field.options), answer)
            if choice is None:
                raise FillError(f"{_said(label)}: none of its {len(field.options)} choices fits {answer!r}")
            _click(label, box.get_by_role("option", name=choice, exact=True).first, OPENS_MS)
            return choice
        before = set(_visible_options(page))
        _click(label, box, 5_000)
        if field.how == "search":
            box.fill(answer)
        options = _listed(page, box, before)
        if field.how == "two-level" and options and _choice_in(options, answer) is None:
            group = self._choose(label, options, answer)
            if group is None:
                _close(page)
                raise FillError(f"{_said(label)}: no group of its list holds {answer!r}")
            shown = set(options)
            _click(label, _option(page, box, group), OPENS_MS)
            options = [o for o in _listed(page, box, shown) if o not in shown] or _listed(page, box, set())
        choice = self._choose(label, options, answer)
        if choice is None:
            _close(page)
            raise FillError(f"{_said(label)}: none of its {len(options)} choices fits {answer!r}")
        _click(label, _option(page, box, choice), OPENS_MS)
        return choice

    def _choose(self, label: str, options: list[str], answer: str) -> str | None:
        """The option that is the answer: its exact words, else one the Fill engine reads as showing it, else the
        model's pick (one question, the field's options), else None."""
        if (found := _choice_in(options, answer)) is not None:
            return found
        if not options or self._pick is None or len(options) > MAX_CHOICES:
            return None
        try:
            place = self._pick(label, options, answer)
        except UsageLimitHit:
            raise  # the day's model use is spent: the run pauses
        except Exception:
            return None  # no model's pick: the field is the student's, as one code can't match
        if place is None:
            return None
        self.picked.append((label, options[place]))
        return options[place]

    def _read_back(self, page: Page, field: Field, put) -> object:
        """What the field shows now, read by plain code from its own element."""
        try:
            if field.how == "text":
                return locate(page, field.role, field.name, field.nth).input_value(timeout=3_000)
            if field.how == "native select":
                shown = locate(page, field.role, field.name, field.nth).evaluate(CHOSEN, timeout=3_000)
                return shown
            if field.how == "radios":
                return next((option for option, (role, name, nth) in zip(field.options, field.controls)
                             if locate(page, role, name, nth).is_checked(timeout=3_000)), "")
            if field.how == "checkbox":
                return "Yes" if locate(page, field.role, field.name, field.nth).is_checked(timeout=3_000) else "No"
            if field.how == "checkboxes":
                return [option for option, (role, name, nth) in zip(field.options, field.controls)
                        if locate(page, role, name, nth).is_checked(timeout=3_000)]
            if field.how == "file":
                names = page.locator("input[type=file]").nth(field.nth).evaluate(FILE_NAMES, timeout=3_000)
                return names[0] if names else ""
            box = locate(page, field.role, field.name, field.nth)
            if field.role == "listbox":
                return next((o for o in box.get_by_role("option", selected=True).all_inner_texts() if o.strip()), "").strip()
            return _shown_choice(box, str(put))
        except Exception:
            return ""

    # --- the step

    def _clear(self, page: Page) -> None:
        """A captcha's challenge is the captcha wait; a pop-up over the form is closed by plain code (apply.attach),
        or it is a Handoff."""
        if captcha.shows(page):
            raise Captcha(CAPTCHA_CHALLENGE, page)
        if said := clear_pop_up(page, self._resume):
            raise Handoff(POP_UP.format(said))

    def _check_step(self, page: Page, here: dict[str, Field]) -> None:
        """Before Next: an error the page shows, a field that went blank or changed once filled, a widget no tree
        shows, a required box only the student may tick, and anything the guards stopped are each a Handoff."""
        self._blocked()
        if new := [a for a in _alerts(page) if a not in self._alerts and ERROR_WORDS.search(a)]:
            raise Handoff(ALERT.format(new[0][:160]))
        now = self._match(form_tree.read(page, open_dropdowns=False))
        for name, field in here.items():
            if name not in self._put or field.how == "file":
                continue
            shown = now.get(name)
            if shown is None or (shown.shows not in ("", ()) and _same(shown.shows, self._readback.get(name))):
                continue
            again = self._read_back(page, field, self._readback.get(name))
            if not _same(again, self._readback.get(name)):
                raise Handoff(RESET.format(repr(_said(self._asked[0].get(name, field.label)))))
        try:
            unread = page.evaluate(UNREADABLE)
        except Exception:
            unread = ""
        if unread:
            raise Handoff(UNREAD.format(self._steps + 1, unread))
        labels, answers = self._asked
        now_shown = {name: (now[name].shows if name in now else field.shows) for name, field in here.items()}
        required = [labels.get(name, field.label) for name, field in here.items()
                    if field.required and name in self._attests and name not in answers
                    and now_shown[name] in ("", (), "No")]
        if required and self._next(page) is not None:
            raise Handoff(TO_TICK.format(self._steps + 1, fill_engine.tick_ask(required)))

    def _next(self, page: Page) -> str | None:
        """The step's Next by its words (apply.steps.NEXT, never one that says it sends or goes back), or None on the
        last step, which shows a button that sends and no Next. Two that could go on: the model says which goes on
        without sending (`generic_fill.next`), or it is a Handoff. Neither a Next nor a button that sends: a Handoff."""
        names = _buttons(page)
        nexts = list(dict.fromkeys(n for n in names if NEXT.search(n) and not SENDS.search(n) and not BACK.search(n)))
        if len(nexts) == 1:
            return nexts[0]
        if not nexts:
            if any(SENDS.search(n) for n in names):
                return None
            raise Handoff(UNCLEAR.format(self._steps + 1))
        place = self._next_button(nexts) if self._next_button else None
        if place is None:
            raise Handoff(MANY_NEXT.format(self._steps + 1, ", ".join(repr(n) for n in nexts[:4])))
        return nexts[place]

    def _open_form(self, page: Page) -> None:
        """A posting page that shows no field: its one Apply link on the page's own site is followed (a navigation,
        no click), or its one Apply button pressed through the guards, and the form waited for. Its whole name must
        be an opener's (OPENS: "Apply for This Job", BambooHR's). None, two that differ, a button in a form (its press would send
        that form: opening a form never needs one sent), or one with a frame inside is a Handoff."""
        links = [el for el in page.get_by_role("link", name=OPENS).all() if el.is_visible()]
        buttons = [el for el in page.get_by_role("button", name=OPENS).all() if el.is_visible()]
        names = {" ".join(str(el.aria_snapshot()).split()) for el in links + buttons}
        if len(names) != 1:
            raise Handoff(NO_OPENER.format(f"{len(names)} found" if names else "none found"))
        target = (links or buttons)[0]
        href = target.evaluate(OPENER_HREF)
        if links and href:
            if target.evaluate(SAME_ORIGIN) is not True:
                raise Handoff(NO_OPENER.format("the one found goes to another site"))
            page.goto(href)
        else:
            if target.evaluate(IN_A_FORM) is not False:
                raise Handoff(NO_OPENER.format("the one found sits in a form, and its press could send it"))
            self._guard_on(page)
            if not self._guard.may_press(target):  # a frame inside it, where the press could land (KAN-710)
                raise Handoff(NO_OPENER.format("a frame sits inside the one found"))
            target.click(timeout=5_000)
        for _ in range(int(PAGE_SETTLES_MS / 250)):
            page.wait_for_timeout(250)
            if form_tree.read(page, open_dropdowns=False):
                break
        self._blocked()


def _click(label: str, element, timeout: float) -> None:
    """Plain code's click on a dropdown or an option, never on one that would submit a form (form_tree.SUBMITS)."""
    if submits(element):
        raise FillError(f"{_said(label)}: its control would send the form, so Apply didn't click it")
    element.click(timeout=timeout)


def _check(label: str, element, ticked: bool) -> None:
    """Plain code's tick of a radio or box, never one that would submit a form (form_tree.SUBMITS)."""
    if submits(element):
        raise FillError(f"{_said(label)}: its control would send the form, so Apply didn't click it")
    element.set_checked(ticked, timeout=5_000)


def _submits_a_sending_form(page: Page, name: str) -> bool:
    """Whether a button named `name` would submit a form that holds a button whose words send (FORM_BUTTONS). One
    Apply can't read counts as one."""
    try:
        for button in page.get_by_role("button", name=name, exact=True).all():
            if any(SENDS.search(words) for words in button.evaluate(FORM_BUTTONS, timeout=3_000)):
                return True
    except Exception:
        return True
    return False


def _said(label: str) -> str:
    """A label as a FillError names its field: the Worker reads the field up to the first colon."""
    return " ".join(label.replace(":", " ").split())


def _same(shown, meant) -> bool:
    if isinstance(shown, tuple):
        shown = list(shown)
    if isinstance(meant, Path):
        meant = meant.name
    return fill_engine.shows(shown, meant)


def _choice_in(options: list[str], answer: str) -> str | None:
    """The option that is the answer by code alone: its exact words, else its words in another case and spacing,
    else the one the Fill engine reads as showing it."""
    if answer in options:
        return answer
    key = " ".join(answer.lower().split())
    found = [o for o in options if " ".join(o.lower().split()) == key]
    if len(found) == 1:
        return found[0]
    found = [o for o in options if fill_engine.shows(o, answer)]
    return found[0] if len(found) == 1 else None


def _alerts(page: Page) -> set[str]:
    try:
        return {" ".join(t.split()) for t in page.get_by_role("alert").filter(visible=True).all_inner_texts() if t.strip()}
    except Exception:
        return set()


def _buttons(page: Page) -> list[str]:
    """The names of the visible buttons, as the tree reads them."""
    names = []
    for node in _flat(form_tree.parse(page.locator("body").aria_snapshot())):
        if node.role == "button" and node.name and node.attrs.get("disabled") != "true":
            names.append(node.name)
    return names


def _flat(nodes):
    for node in nodes:
        yield node
        yield from _flat(node.children)


def _visible_options(page: Page) -> list[str]:
    return [o.strip() for o in page.get_by_role("option").filter(visible=True).all_inner_texts() if o.strip()]


def _listed(page: Page, box, before: set[str]) -> list[str]:
    """The choices an opened dropdown lists: its own listbox's (aria-controls, aria-owns), else the options that
    showed once it opened and weren't showing before, as soon as any show."""
    owned = _owned_listbox(page, box)
    if owned is not None:
        return list(dict.fromkeys(o.strip() for o in owned.get_by_role("option").all_inner_texts() if o.strip()))
    for _ in range(max(1, OPENS_MS // 100)):
        found = list(dict.fromkeys(o for o in _visible_options(page) if o not in before))
        if found:
            return found
        page.wait_for_timeout(100)
    return []


def _option(page: Page, box, choice: str):
    """The option named `choice` in the dropdown's own listbox, else among those showing: only an option, never a
    button or a link of the page's."""
    return (_owned_listbox(page, box) or page).get_by_role("option", name=choice, exact=True).filter(visible=True).first


def _close(page: Page) -> None:
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass


def _shown_choice(box, choice: str) -> str:
    """What a dropdown shows: `choice` when its field's text shows it on a line of its own (a chip, a value), else its
    tree value."""
    try:
        text = box.evaluate(FIELD_TEXT, timeout=3_000)
    except Exception:
        text = ""
    if any(line.strip() == choice for line in str(text).splitlines()):
        return choice
    try:
        found = form_tree.parse(box.aria_snapshot(timeout=3_000))
    except Exception:
        return ""
    value = found[0].value if found else ""
    return value or (box.input_value(timeout=3_000) if _is_input(box) else "")


def _is_input(box) -> bool:
    try:
        return box.evaluate("el => el.tagName === 'INPUT'", timeout=3_000) is True
    except Exception:
        return False
