"""The generic Filler (KAN-861, W2 step 2): it reads a form from the accessibility tree and fills it with plain code,
on Chromium. Run on a Mac, not in CI (a Filler test). The snapshot parser's own tests, with no browser, are in
test_form_tree.py."""

from contextlib import contextmanager

import pytest

from apply import fill_engine, form_tree
from apply.adapters import SetupError
from apply.generic_fill import GenericFiller
from apply.model import FillError, Handoff, MoreQuestions
from apply.plain.demo import SAVED_FORMS, replay


@contextmanager
def chromium():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch()
        except Exception:
            pytest.skip("no Playwright Chromium here")
        try:
            yield browser
        finally:
            browser.close()


@contextmanager
def form(html: str):
    with chromium() as browser:
        page = browser.new_page()
        page.set_content(html)
        yield page


# One of each control the reader tells apart.
EACH = """<form><h2>About you</h2>
<label>First name * <input name=f></label>
<label for=e>Email</label><input id=e type=email value="a@b.co" required>
<label>Cover letter <textarea></textarea></label>
<label>State <select><option value="">Select...</option><option>New York</option><option>Ohio</option></select></label>
<fieldset><legend>Are you authorized to work in the US?</legend>
<label><input type=radio name=a value=y> Yes</label><label><input type=radio name=a value=n> No</label></fieldset>
<p>Will you need sponsorship?</p><label><input type=radio name=s> Yes</label><label><input type=radio name=s> No</label>
<label><input type=checkbox> I am at least 18 years old</label>
<fieldset><legend>Languages</legend><label><input type=checkbox> English</label><label><input type=checkbox> Spanish</label></fieldset>
<p>Resume/CV</p><div><input type=file id=r style="display:none"><button type=button>Attach</button></div>
<div role=combobox aria-label="How did you hear?" aria-controls=hear tabindex=0 onclick="hear.hidden=false">Select</div>
<ul role=listbox id=hear hidden><li role=option>LinkedIn</li><li role=option>A friend</li></ul>
<label>School <input role=combobox aria-autocomplete=list></label>
<input type=hidden name=token value=x><input disabled aria-label="Locked">
</form>"""


def test_the_reader_reads_each_kind_of_control():
    # Fault: any one control read as the wrong kind, with the wrong options or label, or a hidden or disabled box read.
    with form(EACH) as page:
        read = [(f.how, f.label, f.kind, f.required, f.options) for f in form_tree.read(page)]
    assert read == [
        ("text", "First name", "text", True, ()),
        ("text", "Email", "text", True, ()),
        ("text", "Cover letter", "textarea", False, ()),
        ("native select", "State", "select", False, ("New York", "Ohio")),
        ("radios", "Are you authorized to work in the US?", "select", False, ("Yes", "No")),
        ("radios", "Will you need sponsorship?", "select", False, ("Yes", "No")),
        ("checkbox", "I am at least 18 years old", "select", False, ("Yes", "No")),
        ("checkboxes", "Languages", "multi_select", False, ("English", "Spanish")),
        ("dropdown", "How did you hear?", "select", False, ("LinkedIn", "A friend")),
        ("search", "School", "text", False, ()),
        ("file", "Resume/CV", "file", False, ()),
    ]


def test_a_box_named_only_by_its_placeholder_takes_the_words_before_it_and_is_found_again():
    # Fault (Lever's forms, 2026-11-15): every box named "Type your response", one question for all of them; or a
    # nameless box found among the nameless only, so its facts came from another box.
    html = """<ul><li>City ✱ <input placeholder="Type your response"></li>
              <li>School Major: <textarea></textarea></li>
              <li><label>Zip <input></label></li>
              <li>School Minor: <input></li></ul>"""
    with form(html) as page:
        fields = form_tree.read(page)
        assert [(f.label, f.kind, f.required) for f in fields] == [
            ("City", "text", True), ("School Major:", "textarea", False), ("Zip", "text", False), ("School Minor:", "text", False)]
        minor = fields[3]
        form_tree.locate(page, minor.role, minor.name, minor.nth).fill("Math")
        assert page.locator("li").nth(3).locator("input").input_value() == "Math"


LEVER = ["lever-belvedere", "lever-hermeus", "lever-immuta", "lever-rhombus", "lever-shieldai", "lever-xcimer"]


def _key(label: str) -> str:
    return " ".join(label.lower().replace("*", "").split()).rstrip(" :?")


@pytest.mark.parametrize("saved", LEVER)
def test_the_reader_finds_the_engines_questions_on_a_saved_form(saved):
    # Fault: a reader that loses a kind of field the engine reads on a real form. Lever's are the saved forms whose
    # questions the engine reads off the served page with no network (Greenhouse's and Ashby's come from their APIs).
    # Measured 2026-11-15: 164 of the 174 engine questions on the six forms, the rest a self-ID survey the page
    # keeps collapsed and a signature's two parts.
    with chromium() as browser, replay(SAVED_FORMS / saved) as (url, real):
        page = browser.new_page()
        page.goto(url)
        page.wait_for_timeout(1500)
        engine = fill_engine.parse_questions(fill_engine.job_of(real)["site"], page.evaluate("() => document.documentElement.outerHTML"))
        ours = {_key(f.label): f for f in form_tree.read(page)}
    # By its label, or one that adds help text after it ("Race Click to see details about each option.").
    mine = {q.name: next((f for key, f in ours.items() if key == _key(q.label) or key.startswith(_key(q.label) + " ")), None)
            for q in engine}
    found = [q for q in engine if mine[q.name]]
    assert len(found) >= 0.85 * len(engine), [q.label for q in engine if q not in found]
    # The same kind; a list the engine reads from the page's data is one the fill reads as it opens or types (Lever's
    # universities).
    same = [q for q in found if mine[q.name].kind == q.kind or q.kind == "textarea"
            or mine[q.name].how in ("search", "dropdown") and mine[q.name].kind == "text"]
    assert len(same) >= 0.95 * len(found), [(q.label, q.kind, mine[q.name].kind) for q in found if q not in same]


# --- the Filler on fake forms


class Site:
    """A job site whose one page is `page`, as OnePage gives it."""

    def __init__(self, page):
        self.page = page

    @contextmanager
    def open(self, url):
        yield self.page


def filled(page, answers: dict, filler=None, more: dict | None = None):
    """Read the form, answer each question by its label (`answers`, then `more` for a later step's), and fill it to its
    last step: the filler, its readback and every question asked."""
    filler = filler or GenericFiller()
    questions = filler.question_set("https://jobs.example.com/1", Site(page))
    given = {**answers, **(more or {})}
    planned = {q.name: given[q.label] for q in questions if q.label in given}
    for _ in range(10):
        try:
            return filler, filler.fill(page, questions, planned), questions
        except MoreQuestions as asked:
            questions = [*questions, *asked.questions]
            planned |= {q.name: given[q.label] for q in asked.questions if q.label in given}
    raise AssertionError("the fill never ended")


SUBMIT = "<button type=submit>Submit application</button>"


def test_the_filler_fills_each_plain_control_and_reads_it_back(tmp_path):
    # Fault: any one kind of control left blank, filled with the wrong option, or read back as something else.
    resume = tmp_path / "cover.pdf"
    resume.write_bytes(b"%PDF-1.4")
    html = f"""<form method=post action="/apply">
      <label>First name <input></label><label>Why us? <textarea></textarea></label>
      <label>State <select><option value="">Select...</option><option>New York</option><option>Ohio</option></select></label>
      <fieldset><legend>Authorized?</legend><label><input type=radio name=a> Yes</label><label><input type=radio name=a> No</label></fieldset>
      <label><input type=checkbox> I am at least 18 years old</label>
      <fieldset><legend>Languages</legend><label><input type=checkbox> English</label><label><input type=checkbox> Spanish</label></fieldset>
      <label>Cover letter <input type=file></label>{SUBMIT}</form>"""
    answers = {"First name": "Test", "Why us?": "Robots.", "State": "Ohio", "Authorized?": "No",
               "I am at least 18 years old": "Yes", "Languages": ["Spanish"], "Cover letter": resume}
    with form(html) as page:
        _, readback, questions = filled(page, answers)
        names = {q.label: q.name for q in questions}
        assert {label: readback[names[label]] for label in answers} == {
            "First name": "Test", "Why us?": "Robots.", "State": "Ohio", "Authorized?": "No",
            "I am at least 18 years old": "Yes", "Languages": ["Spanish"], "Cover letter": "cover.pdf"}
        assert page.locator("select").input_value() == "Ohio"
        assert page.get_by_role("checkbox", name="English").is_checked() is False


@pytest.mark.xdist_group("plain-worker")
def test_the_filler_fills_the_same_controls_on_a_plain_worker(tmp_path):
    # Fault: a call the generic Filler makes that a plain Worker's page (apply.plain.page) lacks or reads otherwise:
    # W2 asks for one Filler on CDP and plain Workers alike.
    from plain_fakes import fake_page, have_chrome_for_testing

    if not have_chrome_for_testing():
        pytest.skip("needs Chrome for Testing (uv run playwright install chromium)")
    html = f"""<form method=post action="/apply"><label>First name <input></label>
      <label>State <select><option value="">Select...</option><option>New York</option><option>Ohio</option></select></label>
      <fieldset><legend>Authorized?</legend><label><input type=radio name=a> Yes</label><label><input type=radio name=a> No</label></fieldset>
      <label><input type=checkbox> I am at least 18 years old</label>{SUBMIT}</form>"""
    answers = {"First name": "Test", "State": "Ohio", "Authorized?": "No", "I am at least 18 years old": "Yes"}
    with fake_page(lambda route: route.fulfill(body=html, content_type="text/html"), url="https://jobs.example.com/1") as page:
        _, readback, questions = filled(page, answers)
    names = {q.label: q.name for q in questions}
    assert {label: readback[names[label]] for label in answers} == answers


def test_a_field_that_doesnt_show_its_answer_is_a_fill_error_that_names_it():
    # Fault: a read-back that trusts the fill, so a box the page clears goes to the Pre-submit check as filled, or a
    # FillError that names no field, which the Worker can't make a Needs-you item of.
    html = f"""<form><label>Phone <input oninput="this.value = ''"></label>{SUBMIT}</form>"""
    with form(html) as page, pytest.raises(FillError, match=r"^Phone: the page shows '' after Apply filled it"):
        filled(page, {"Phone": "5551234567"})


@pytest.mark.parametrize(("trap", "said"), [
    ("""<div role=alert id=a></div><script>document.querySelector('input').addEventListener('change',
        () => a.textContent = 'Please enter a valid name')</script>""", "shows an error Apply didn't expect"),
    ("""<label>Last name <input id=l></label><script>l.addEventListener('change',
        () => document.querySelector('input').value = '')</script>""", "'First name' went blank or changed after Apply filled it"),
    ("""<canvas width=300 height=100></canvas>""", "a drawing area"),
])
def test_a_page_in_a_state_the_fill_didnt_expect_is_the_students(trap, said):
    # Fault: each of W2's Handoffs filled past: an error the page showed, a field it reset, a widget no tree shows.
    html = f"<form><label>First name <input></label>{trap}{SUBMIT}</form>"
    with form(html) as page, pytest.raises(Handoff, match=said):
        filled(page, {"First name": "Test", "Last name": "Person"})


def test_the_filler_never_submits():
    with pytest.raises(SetupError, match="never presses Submit"):
        GenericFiller().submit(None)
