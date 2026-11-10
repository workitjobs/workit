"""PR 477's second adversarial review (KAN-710): each case is a way it found to send, and each must send nothing."""

import pytest
from test_submit_guard_hostile import FINAL, SAVE, START, _settle, cdp, plain

from apply import claude_fill

STEP2 = "/acme/jobs/123/step2"
ALWAYS = {STEP2: "<title>Two</title><input name=next>"}

# Find each guard's token in the name of its install mark on window, then lift that guard by its own control event.
STEAL = """<script>
window.lifted = [];
for (const n of Object.getOwnPropertyNames(window)) {
  const m = /^__(applyRehearsal|applyDrive)Guard([0-9a-f]{32})$/.exec(n);
  if (!m) continue;
  const e = new CustomEvent('__' + m[1] + 'Control' + m[2], {detail: JSON.stringify({lift: {}}), cancelable: true});
  dispatchEvent(e);
  window.lifted.push(m[1] + ':' + e.defaultPrevented);
}
</script>"""

SAVE_FORM = (f'<form id=f method=post action="{SAVE}"><input name=first value=Test>'
             '<input type=hidden name=submit value=1><button id=s>Submit application</button></form>')
FORM = f'<form id=f method=post action="{FINAL}"><input name=first value=Test><button id=s>Submit application</button></form>'

LOAD = {
    "CONTROL no token, form.submit()": f"<title>Apply</title>{FORM}"
        + "<script>setTimeout(() => document.getElementById('f').submit(), 200);</script>",
    "token from the install mark, then form.submit()": f"<title>Apply</title>{FORM}" + STEAL
        + "<script>setTimeout(() => document.getElementById('f').submit(), 200);</script>",
    "token from the install mark, then fetch": "<title>Apply</title>" + STEAL
        + f"<script>setTimeout(() => fetch('{FINAL}', {{method: 'POST', body: 'first=Test'}}), 200);</script>",
}


@pytest.fixture(autouse=True)
def quick_steps(monkeypatch):
    monkeypatch.setattr(claude_fill, "STEP_SHOWS_MS", 1500)


@pytest.mark.parametrize("name", list(LOAD))
def test_load_after_guard(name):
    """The page loaded after guard() and DriveGuard: reload so both are init scripts."""
    with cdp({START: LOAD[name]} | ALWAYS) as (page, _, site):
        site.sent.clear(); site.bodies.clear()  # the fixture's first load was unguarded
        page.reload()
        _settle(page, 1500)
        print("lifted:", page.evaluate("window.lifted"))
    assert site.applications() == []


PLAIN_LOAD = {"CONTROL no token": f"<title>Apply</title>{SAVE_FORM}"
    + "<script>setTimeout(() => HTMLFormElement.prototype.submit.call(document.getElementById('f')), 200);</script>",
    "token from the install mark, then form.submit() to the save URL": f"<title>Apply</title>{SAVE_FORM}" + STEAL
    + "<script>setTimeout(() => HTMLFormElement.prototype.submit.call(document.getElementById('f')), 200);</script>"}


@pytest.mark.parametrize("name", list(PLAIN_LOAD))
def test_plain_load(name):
    with plain({START: PLAIN_LOAD[name]} | ALWAYS) as (page, _drive, site):
        site.sent.clear(); site.bodies.clear()  # the fixture's first load was unguarded
        page.reload()
        _settle(page, 2000)
    assert site.applications() == []



# The drive guard put on a page that is already open (DriveGuard._in_frames: frame.evaluate in the page's own world,

# --- KAN-725's vouched Apply

def test_tal_page_vouches_for_itself_with_the_stolen_token():
    from test_submit_guard import _press_tal_apply
    steal = STEAL.replace("{lift: {}}", "{start: true}").replace("<script>", "<script>setInterval(() => {", 1).replace("</script>", "}, 50);</script>", 1)
    posts, blocked = _press_tal_apply(page=steal, start=False, rehearsal=True)
    assert posts == [] and blocked
