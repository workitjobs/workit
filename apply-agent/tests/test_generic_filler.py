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
      <label><input type=checkbox> I am at least 18 years old</label>
      {DROPDOWN % '<li role=option>A friend</li><li role=option>Online job board</li>'}{SUBMIT}</form>"""
    answers = {"First name": "Test", "State": "Ohio", "Authorized?": "No", "I am at least 18 years old": "Yes",
               "How did you hear about us?": "A friend"}
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


def test_a_radio_choice_code_cant_match_is_the_models_pick_and_a_none_is_the_students():
    # Fault: a choice whose words aren't the answer's left blank though the model could name it, or a "none" from the
    # model (or a failed call) taken as a pick.
    html = f"""<form><fieldset><legend>How did you hear about us?</legend>
      <label><input type=radio name=h> A friend</label><label><input type=radio name=h> Online job board</label>
      </fieldset>{SUBMIT}</form>"""
    asked = []
    with form(html) as page:
        filler = GenericFiller(pick=lambda q, options, a: asked.append((q, options, a)) or 1)
        _, readback, _ = filled(page, {"How did you hear about us?": "LinkedIn"}, filler)
        assert asked == [("How did you hear about us?", ["A friend", "Online job board"], "LinkedIn")]
        assert readback == {"g1": "Online job board"} and filler.picked == [("How did you hear about us?", "Online job board")]
    with form(html) as page, pytest.raises(FillError, match="^How did you hear about us[?]: no option fits 'LinkedIn'"):
        filled(page, {"How did you hear about us?": "LinkedIn"}, GenericFiller(pick=lambda q, options, a: None))


DROPDOWN = """<div role=combobox aria-label="How did you hear about us?" aria-controls=hear tabindex=0
  onclick="hear.hidden = false">Select</div>
<ul role=listbox id=hear hidden>%s</ul>
<script>for (const o of document.querySelectorAll('#hear [role=option]')) o.addEventListener('click', () => {
  if (o.dataset.group) { hear.innerHTML = o.dataset.group.split('|').map((x) => '<li role=option>' + x + '</li>').join('');
    for (const n of hear.children) n.addEventListener('click', () => { document.querySelector('[role=combobox]').textContent = n.textContent; hear.hidden = true; });
    return; }
  document.querySelector('[role=combobox]').textContent = o.textContent; hear.hidden = true; });</script>"""


def test_a_dropdown_choice_code_cant_match_is_the_models_pick_and_code_clicks_it():
    # Fault: a dropdown left blank when the answer's words aren't an option's, or a pick that never reaches the page.
    asked = []

    def pick(question, options, answer):
        asked.append((question, options, answer))
        return options.index("Online job board")
    html = f"<form>{DROPDOWN % '<li role=option>A friend</li><li role=option>Online job board</li>'}{SUBMIT}</form>"
    with form(html) as page:
        filler = GenericFiller(pick=pick)
        filled(page, {"How did you hear about us?": "LinkedIn"}, filler)
        assert asked == [("How did you hear about us?", ["A friend", "Online job board"], "LinkedIn")]
        assert page.get_by_role("combobox").inner_text() == "Online job board"
        assert filler.picked == [("How did you hear about us?", "Online job board")]


def test_a_two_level_list_opens_the_group_the_model_picks_and_code_finds_the_answer_in_it():
    # Fault (W2's example, Workday's "How did you hear about us?"): the groups taken as the choices, so "LinkedIn"
    # fits none and the field is the student's, though one group holds it.
    groups = ('<li role=option aria-haspopup=listbox data-group="Indeed|LinkedIn">Job Board</li>'
              '<li role=option aria-haspopup=listbox data-group="Instagram|TikTok">Social Media</li>')
    picks = []
    html = f"<form>{DROPDOWN % groups}{SUBMIT}</form>"
    with form(html) as page:
        filler = GenericFiller(pick=lambda q, options, a: picks.append(options) or 0)
        filled(page, {"How did you hear about us?": "LinkedIn"}, filler)
        assert picks == [["Job Board", "Social Media"]]  # one question, the groups; code found LinkedIn in Job Board
        assert page.get_by_role("combobox").inner_text() == "LinkedIn"


def test_a_search_box_is_typed_into_and_its_listed_choice_clicked():
    # Fault: a search box (no choices until one types) typed into and left, its typed text read back as the answer.
    html = f"""<form><label>School <input role=combobox aria-controls=sl id=s
      oninput="sl.innerHTML = this.value ? '<li role=option>State University of New York at Stony Brook</li>' : ''"></label>
      <ul role=listbox id=sl></ul><script>sl.addEventListener('click', (e) => {{ s.value = e.target.textContent; sl.innerHTML = ''; }});</script>{SUBMIT}</form>"""
    with form(html) as page:
        filler = GenericFiller(pick=lambda q, options, a: 0)
        filled(page, {"School": "Stony Brook University"}, filler)
        assert page.locator("#s").input_value() == "State University of New York at Stony Brook"


STEPS = """<form id=f onsubmit="event.preventDefault()"><div id=step>
  <label>First name <input name=first></label><button type=button id=n onclick="go()">Next</button></div></form>
<script>function go() { step.innerHTML = '<label>Major <input name=major></label>' + %s; }</script>"""


def test_a_form_in_steps_is_filled_a_step_at_a_time_to_its_last_and_never_sent():
    # Fault: a fill that stops at the first Next, misses the next step's questions, or presses the step that sends.
    html = STEPS % """'<button type=submit onclick="window.sent = true">Submit application</button>'"""
    with form(html) as page:
        filler, readback, questions = filled(page, {"First name": "Test"}, more={"Major": "Physics"})
        assert [q.label for q in questions] == ["First name", "Major"]
        assert readback == {"g1": "Test", "g2": "Physics"} and filler.shown_so_far == readback
        assert page.evaluate("window.sent") is None


def test_two_buttons_that_could_go_on_are_the_models_pick_and_none_is_a_handoff():
    # Fault: a step with "Save and continue later" beside "Continue" pressed on the first that says continue, or a
    # step whose end isn't clear filled past instead of handed to the student.
    two = """'<button type=button onclick="window.later = true">Save and continue later</button>'
             + '<button type=button onclick="step.innerHTML = \\'<button type=submit>Submit</button>\\'">Continue</button>'"""
    asked = []
    with form(STEPS % two) as page:
        filled(page, {"First name": "Test"}, GenericFiller(next_button=lambda names: asked.append(names) or 1))
        assert asked == [["Save and continue later", "Continue"]] and page.evaluate("window.later") is None
    with form(STEPS % two) as page, pytest.raises(Handoff, match="more than one button that could go on"):
        filled(page, {"First name": "Test"})
    with form(STEPS % "'<button type=button>Done</button>'") as page, pytest.raises(Handoff, match="no Next and no button that sends on page 2"):
        filled(page, {"First name": "Test"}, more={"Major": "Physics"})


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


def test_a_posting_page_with_one_apply_button_opens_its_form_and_never_sends():
    # Fault (BambooHR's posting): a page whose form shows only once its Apply button is pressed read as no form, or
    # a page with two Apply buttons pressed on either.
    html = """<h1>Intern</h1><p>Build robots.</p><button id=a onclick="a.remove(); f.hidden = false">Apply for This Job</button>
      <form id=f hidden><label>First name <input></label><button type=submit>Submit Application</button></form>"""
    with form(html) as page:
        _, readback, _ = filled(page, {"First name": "Test"})
        assert readback == {"g1": "Test"}
    with form(html.replace("<h1>", "<button>Apply now</button><h1>")) as page, pytest.raises(Handoff, match="no one Apply button"):
        filled(page, {"First name": "Test"})


def test_an_apply_link_to_another_site_is_never_followed():
    # Fault (the adversarial review): the Filler goes on to another site's page and fills it, and gives it files.
    html = """<h1>Intern</h1><a href="https://elsewhere.example.org/apply">Apply now</a>"""
    with form(html) as page, pytest.raises(Handoff, match="goes to another site"):
        filled(page, {})
    assert page.url == "about:blank"


def test_the_filler_never_submits():
    with pytest.raises(SetupError, match="never presses Submit"):
        GenericFiller().submit(None)
