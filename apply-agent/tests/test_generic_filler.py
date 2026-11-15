"""The generic Filler (KAN-861, W2 step 2): it reads a form from the accessibility tree and fills it with plain code,
on Chromium. Run on a Mac, not in CI (a Filler test). The snapshot parser's own tests, with no browser, are in
test_form_tree.py."""

from contextlib import contextmanager

import pytest

from apply import fill_engine, form_tree
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
