"""A plain Worker's text reaches a box that takes only a keyboard's text (KAN-716).

amazon.jobs's Job-specific questions showed every answer a plain Worker typed (Claude fill's fill,
Ask, the tile's text and keys) and took none: "This field is required" stayed, its auto-save
failed, and a reload emptied the box. Every such input was a synthetic event or an editing
command, and neither fires what a keyboard does: execCommand("insertText") gives `input` but no
`beforeinput` or `textInput`, and a synthetic event is untrusted. AMAZON_LIKE is a box that takes
its value only from an `input` that a trusted `beforeinput` came before, as a keyboard's text has.

- The control (Playwright's Chromium, page/dom.js without `trusted`): the old path shows the text,
  and the box takes none of it, as on amazon.jobs.
- On a plain Worker (Chrome for Testing, the worker extension's chrome.debugger): fill, type,
  keyboard.insert_text, the tile's text and keys, and Backspace all reach it, trusted.
- The trusted path types only into the field the call chose, and Enter never sends a form.
"""

import json
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from apply.plain import extension
from apply.plain.bridge import PortError

PAGE_DIR = Path(extension.__file__).resolve().parents[3] / "worker-extension" / "page"
HOST = "https://jobs.example.com"

# Two boxes as amazon.jobs's behave: what each holds is set only by text that a trusted beforeinput
# announced; its error shows until it holds a value. `taken` is what the form would auto-save.
AMAZON_LIKE = """<!doctype html><title>Job-specific questions</title>
<form id=form method=post action="/acme/jobs/123/apply">
<label for=why>Describe your experience</label><textarea id=why></textarea><span id=why-error>This field is required</span>
<label for=school>Which university are you currently attending?</label><input id=school><span id=school-error>This field is required</span>
<label for=other>Something else</label><input id=other>
<fieldset><legend>Will you need sponsorship?</legend><label><input type=radio name=sponsor value=Yes> Yes</label>
<label><input type=radio name=sponsor value=No> No</label></fieldset>
<button id=go>Continue</button></form>
<script>
window.taken = {}; window.events = []; window.sent = 0;
addEventListener('pointerup', (e) => { if (e.isTrusted) window.upOn = e.composedPath()[0].id || e.composedPath()[0].tagName; }, true);
// Auto-save: what the form took goes to the server, and a reload shows only what the server holds.
const save = () => fetch('/acme/jobs/123/save', {method: 'PUT', body: JSON.stringify(taken)});
for (const [id, value] of Object.entries(window.saved || {})) {
  if (id === 'sponsor') document.querySelector(`input[name=sponsor][value=${value}]`).checked = true;
  else document.getElementById(id).value = value;
}
// Its radios take only a trusted click, as amazon.jobs's kept no radio a synthetic click set.
for (const radio of document.querySelectorAll('input[type=radio]')) radio.addEventListener('click', (e) => {
  events.push('sponsor:click:' + e.isTrusted);
  if (e.isTrusted) { taken.sponsor = radio.value; save(); }
});
for (const box of document.querySelectorAll('textarea, input')) {
  let announced = false;
  box.addEventListener('beforeinput', (e) => { if (e.isTrusted) announced = true; });
  box.addEventListener('input', (e) => {
    events.push(box.id + ':' + e.type + ':' + e.isTrusted);
    if (!announced) return;
    announced = false;
    taken[box.id] = box.value;
    save();
    const error = document.getElementById(box.id + '-error');
    if (error) error.hidden = box.value !== '';
  });
}
form.addEventListener('submit', (e) => { e.preventDefault(); window.sent++; });
go.addEventListener('click', () => { window.pressed = (window.pressed || 0) + 1; });
</script>"""


def test_the_old_untrusted_path_shows_the_text_and_the_box_takes_none(tmp_path):
    """The control, in Playwright's Chromium: page/dom.js's fill, keys and insert without `trusted`."""
    injected = extension.generated()["injected.js"].decode()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(AMAZON_LIKE)
        for script in (injected, (PAGE_DIR / "dom.js").read_text()):
            page.add_script_tag(content=script)
        run = lambda method, *args: page.evaluate("([m, a]) => __applyDom.run(m, a)", [method, list(args)])
        assert run("check", "input[value=No]", True) == {"ok": None}
        assert run("fill", "#why", "C++ projects") == {"ok": None}
        assert run("type", "#school", "Acme") == {"ok": None}
        run("insert", " College")
        shown = page.evaluate("() => [why.value, school.value, document.querySelector('input[value=No]').checked]")
        taken = page.evaluate("() => taken")
        browser.close()
    assert shown == ["C++ projects", "Acme College", True]
    assert taken == {}


def test_with_trusted_a_text_call_asks_the_service_worker_to_type_it(tmp_path):
    """page/dom.js's side of the seam, in Playwright's Chromium: a request for the chosen field, not text."""
    injected = extension.generated()["injected.js"].decode()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(AMAZON_LIKE)
        for script in (injected, (PAGE_DIR / "dom.js").read_text()):
            page.add_script_tag(content=script)
        run = lambda method, *args: page.evaluate("([m, a]) => __applyDom.run(m, a, {trusted: true})", [method, list(args)])
        fill = run("fill", "#why", "C++")["ok"]
        nothing_typed = page.evaluate("() => why.value")
        no_debugger = run("landed", fill["token"], False)["ok"]  # the debugger never sent it: typed as before
        typed = run("type", "#school", "SB")["ok"]
        key = run("keys", "S")["ok"]
        landed = run("landed", key["token"], True)["ok"]  # sent, never arrived (a guard took it): an error, not typed again
        enter = run("keys", "Enter")["ok"]
        backspace = run("keys", "Backspace")["ok"]
        button = run("keys", "a") if page.evaluate("() => { go.focus(); return true }") else None
        browser.close()
    assert fill["__applyType"] == "C++" and fill["token"] and nothing_typed == ""
    assert no_debugger == {"trusted": False, "fallback": True}
    assert typed["__applyKeys"] == "SB" and typed["chosen"]
    assert key["__applyType"] == "S" and key["after"] == ["keyup", ["S"]]
    assert landed == {"missed": "the text did not reach the field"}
    assert enter is None and backspace["__applyKey"] == "Backspace"
    assert button == {"ok": None}  # a key on a button: no text for anyone to type


# --- on a plain Worker

def _plain_or_skip():
    from plain_fakes import have_chrome_for_testing
    if not have_chrome_for_testing():
        pytest.skip("needs Chrome for Testing (uv run playwright install chromium)")


class Site:
    """The fake job system: it keeps what the form auto-saves, and a page it sends shows only that."""

    def __init__(self, html: str):
        self.html, self.posts, self.saved = html, [], {}

    def handle(self, route) -> None:
        request = route.request
        if request.url.endswith("/save"):
            self.saved = request.post_data_json or {}
            return route.fulfill(body="{}", content_type="application/json")
        if request.method not in ("GET", "HEAD", "OPTIONS") and request.url.startswith(HOST):
            self.posts.append(request.url)
        route.fulfill(body=f"<script>window.saved = {json.dumps(self.saved)}</script>" + self.html, content_type="text/html")


@pytest.fixture
def amazon():
    _plain_or_skip()
    from plain_fakes import fake_page

    site = Site(AMAZON_LIKE)
    with fake_page(site.handle, url=HOST + "/questions") as page:
        yield page, site


def taken(page) -> dict:
    return page.evaluate("() => taken")


def tile(page, event: dict):
    return page.worker.call("tile.input", tab=page.tab, event=event, by="lisul")


def test_fill_type_and_insert_text_reach_a_box_that_takes_only_a_keyboards_text(amazon):
    page, _ = amazon
    page.locator("#why").fill("C++: a course project.")
    page.locator("#school").press_sequentially("Acme")
    page.keyboard.insert_text(" College")
    page.locator("#why").fill("C++ projects")  # a second fill replaces it, as Playwright's does

    assert taken(page) == {"why": "C++ projects", "school": "Acme College"}
    assert page.evaluate("() => [why.value, school.value]") == ["C++ projects", "Acme College"]
    assert page.evaluate("() => [document.getElementById('why-error').hidden, document.getElementById('school-error').hidden]") == [True, True]
    assert page.evaluate("() => events.filter(e => e.endsWith(':false'))") == []  # every input trusted


def test_the_tiles_text_and_keys_reach_it_as_his_keyboards_do(amazon):
    page, _ = amazon
    page.locator("#school").focus()
    for event in ({"type": "text", "text": "A"}, {"type": "text", "text": "cme Collegex"}, {"type": "key", "key": "Backspace"},
                  {"type": "key", "key": "ArrowLeft"}, {"type": "text", "text": "!"}, {"type": "key", "key": "Delete"}):
        tile(page, event)

    assert page.input_value("#school") == "Acme Colleg!"
    assert taken(page) == {"school": "Acme Colleg!"}


def test_enter_never_sends_the_form_from_a_field_or_its_submit_button(amazon):
    # On amazon.jobs a synthetic Enter in a box clicked the form's submit button and went on to Review.
    page, site = amazon
    page.locator("#school").fill("Acme College")
    page.locator("#school").press("Enter")
    page.keyboard.press("Enter")
    tile(page, {"type": "key", "key": "Enter"})
    page.locator("#go").focus()
    page.keyboard.press("Enter")
    tile(page, {"type": "key", "key": "Enter"})
    page.wait_for_timeout(500)

    assert page.evaluate("() => [window.sent, window.pressed || 0]") == [0, 0]
    assert site.posts == []
    assert page.url.endswith("/questions")


def test_trusted_text_goes_only_into_the_field_the_call_chose(amazon):
    # A page that moves the focus as a key goes down: the key's text never lands in the other box.
    page, _ = amazon
    page.evaluate("() => school.addEventListener('keydown', () => other.focus())")
    page.locator("#school").press_sequentially("ab")
    page.evaluate("() => other.addEventListener('focus', () => go.focus())")
    with pytest.raises(PortError, match="the field lost the focus"):  # checked just before the text goes: nothing sent
        page.locator("#other").press("x")

    assert page.evaluate("() => [school.value, other.value]") == ["", ""]
    assert taken(page) == {}


def test_the_tiles_text_reaches_such_a_box_in_a_cross_origin_frame(amazon):
    # Another site's frame runs in its own process: the trusted text still reaches its focused box.
    page, _ = amazon
    page.evaluate("() => new Promise(done => { const f = document.createElement('iframe'); f.onload = done;"
                  " f.src = 'https://apply.example.org/inner'; document.body.append(f); })")
    inner = next(f for f in page.frames if "example.org" in f.url)
    frame, box = page.locator("iframe").bounding_box(), inner.locator("#school").bounding_box()
    page.mouse.click(frame["x"] + box["x"] + 5, frame["y"] + box["y"] + 5)  # as the tile's press does
    tile(page, {"type": "text", "text": "A"})
    tile(page, {"type": "text", "text": "CU"})

    assert inner.input_value("#school") == "ACU"
    assert inner.evaluate("() => taken") == {"school": "ACU"}


def test_a_radio_clicked_and_text_typed_survive_a_reload(amazon):
    # Live on amazon.jobs (2026-11-10): the page said "Progress auto-saved", and a reload showed the box empty and
    # the radios an earlier Ask set blank. Here only what the server holds comes back after a reload.
    page, site = amazon
    page.get_by_role("radio", name="No").check()
    page.locator("#why").fill("C++ projects")
    page.locator("#school").press_sequentially("ACU")
    page.wait_for_timeout(300)  # the last auto-save
    page.reload()

    assert site.saved == {"sponsor": "No", "why": "C++ projects", "school": "ACU"}
    assert page.evaluate("() => [why.value, school.value, document.querySelector('input[value=No]').checked]") == [
        "C++ projects", "ACU", True]


def test_a_trusted_click_makes_no_move_first_for_a_page_to_time_a_change_by(amazon):
    # The page would put its Continue under the pointer as it comes: a trusted click sends no move before its press.
    page, site = amazon
    page.evaluate("""() => document.querySelector('input[value=Yes]').addEventListener('pointermove', () => {
      const box = document.querySelector('input[value=Yes]').getBoundingClientRect();
      Object.assign(go.style, {position: 'fixed', left: box.left - 20 + 'px', top: box.top - 20 + 'px', width: '80px', height: '60px', zIndex: 9});
    }, true)""")
    page.get_by_role("radio", name="Yes").check()

    assert page.evaluate("() => [window.pressed || 0, window.sent, window.upOn]") == [0, 0, "INPUT"]
    assert site.saved == {"sponsor": "Yes"} and site.posts == []


@pytest.mark.parametrize("when", ["pointerdown"])
def test_a_trusted_click_reaches_only_the_choice_it_was_for(amazon, when):
    # A page that puts its Continue under the pointer as the press goes down: nothing is pressed, and Apply hears
    # that its click missed.
    page, site = amazon
    page.evaluate("""(when) => document.querySelector('input[value=Yes]').addEventListener(when, () => {
      const box = document.querySelector('input[value=Yes]').getBoundingClientRect();
      Object.assign(go.style, {position: 'fixed', left: box.left - 20 + 'px', top: box.top - 20 + 'px', width: '80px', height: '60px', zIndex: 9});
    }, true)""", when)
    with pytest.raises(PortError, match="KAN-716 trusted input"):
        page.get_by_role("radio", name="Yes").check()
    page.wait_for_timeout(300)

    assert page.evaluate("() => [window.pressed || 0, window.sent]") == [0, 0]
    assert page.evaluate("() => window.upOn") == "go"  # the press did land on Continue, and went no further
    assert site.posts == []


SMOOTH = """<!doctype html><style>html { scroll-behavior: smooth }</style><div style="height: 3000px"></div>
<label><input type=radio id=r name=a> Yes</label><div style="height: 3000px"></div>"""


def test_a_choice_below_the_fold_of_a_smooth_scrolling_page_is_clicked(amazon):
    # Bootstrap's reboot sets scroll-behavior: smooth; the point is read once the scroll is done, not mid-way.
    page, site = amazon
    site.html = SMOOTH
    page.reload()
    page.locator("#r").click()

    assert page.evaluate("() => r.checked") is True


def test_text_whose_field_goes_to_another_frame_raises_and_lands_nowhere(amazon):
    page, _ = amazon
    page.evaluate("""() => new Promise(done => { const f = document.createElement('iframe'); f.onload = done;
      f.src = '/inner'; document.body.append(f); })""")
    inner = next(f for f in page.frames if f.url.endswith("/inner"))
    page.evaluate("() => school.addEventListener('focus', () => document.querySelector('iframe').contentDocument.getElementById('why').focus())")
    with pytest.raises(PortError, match="KAN-716 trusted input"):
        page.locator("#school").fill("Acme")

    assert inner.input_value("#why") == "" and page.input_value("#school") == ""


def test_the_drive_guards_checks_on_trusted_input_act_on_a_plain_worker(amazon):
    # PlainDriveGuard sets the page's flags now that a plain Worker's text is trusted: Ask's typing in a password box is
    # refused by the page's guard, and an error for Apply; out of Ask, the same box takes it.
    from apply.plain.guards import PlainDriveGuard

    page, _ = amazon
    page.evaluate("() => { const pw = document.createElement('input'); pw.type = 'password'; pw.id = 'pw'; document.body.append(pw); }")
    drive = PlainDriveGuard(page)
    drive.arm()
    drive.asking(True)
    flags = page.evaluate("() => [window.__applyAsking, window.__applyDriving]")
    with pytest.raises(PortError, match="a guard refused it"):
        page.locator("#pw").fill("hunter2")
    refused = page.input_value("#pw")
    drive.asking(False)
    page.locator("#pw").fill("hunter2")

    assert flags == [True, True] and refused == "" and page.input_value("#pw") == "hunter2"
