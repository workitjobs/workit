"""PR 477's second adversarial review (KAN-710): each case is a way it found to send, and each must send nothing."""

import pytest
from test_submit_guard_hostile import FINAL, SAVE, START, _settle, cdp, plain

from apply import claude_fill, submit_guard

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


# after its code, as a live run's Claude fill does): a page that wrapped addEventListener first hears the control
# event's name, token and all. No install-mark read here.
HOOK = """<script>
const add = EventTarget.prototype.addEventListener;
window.heard = [];
EventTarget.prototype.addEventListener = function (type, ...rest) {
  if (/^__applyDriveControl[0-9a-f]{32}$/.test(String(type))) heard.push(String(type));
  return add.call(this, type, ...rest);
};
setInterval(() => {
  for (const t of heard) dispatchEvent(new CustomEvent(t, {detail: JSON.stringify({lift: {}})}));
}, 100);
</script>"""

LIVE = {
    "drive token heard through a wrapped addEventListener, then fetch": "<title>Apply</title>" + HOOK
        + f"<script>setTimeout(() => fetch('{FINAL}', {{method: 'POST', body: 'first=Test'}}), 1000);</script>",
    "drive token heard, then Claude's click on Submit goes through": f"<title>Apply</title>{FORM}" + HOOK,
    "RegExp exec poisoned before the drive guard came, then fetch": "<title>Apply</title><script>RegExp.prototype.exec = () => null;</script>"
        + f"<script>setTimeout(() => fetch('{FINAL}', {{method: 'POST', body: 'first=Test'}}).catch(() => {{}}), 1000);</script>",
    "CONTROL no hook, fetch": "<title>Apply</title>"
        + f"<script>setTimeout(() => fetch('{FINAL}', {{method: 'POST', body: 'first=Test'}}).catch(() => {{}}), 1000);</script>",
    "CONTROL no hook, Claude's click on Submit": f"<title>Apply</title>{FORM}",
}


# How the page was opened: by a Worker, which puts the drive guard's init script on before its first load
# (submit_guard.on_open, browsers.py), or by code that skips that, so DriveGuard puts its block-only copy in after the
# page's own code. A page that replaced a built-in first defeats any copy put in after it: only the first applies.
OPENED = {"by a Worker": True, "by other code": False}
CASES = [(name, opened) for name in LIVE for opened in OPENED if OPENED[opened] or "RegExp" not in name]


@pytest.mark.parametrize("name, opened", CASES, ids=[f"{n}, {o}" for n, o in CASES])
def test_live_run_drive_guard_only(name, opened):
    """A live run: no rehearsal guard, only Claude fill's DriveGuard on the open page."""
    from playwright.sync_api import sync_playwright
    from test_submit_guard_hostile import HOST, Site

    from apply.submit_guard import DriveGuard

    site = Site({START: LIVE[name]} | ALWAYS)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        context.route(lambda url: True, site.handle)
        page = context.new_page()
        if OPENED[opened]:
            submit_guard.on_open(page)
        page.goto(HOST + START)
        drive = DriveGuard(page)
        drive.arm()
        _settle(page, 600)
        if "Claude's click" in name:
            try:
                page.locator("#s").click(timeout=2000)  # what Claude's browser_click is: trusted
            except Exception:
                pass
        _settle(page, 1500)
        print("blocked:", drive.blocked())
        browser.close()
    assert site.applications() == []


# A plain Worker: the extension's real touch (the run's token) comes, then its synthetic pointerdown; the page's
# pointerdown handler clicks its own button first, so that untrusted click is the one the 1 s window counts.
HIJACK = f"""<title>Apply</title><label>First <input name=first></label><button id=b type=button>Next</button>
<form id=f2 method=post action="{SAVE}"><input type=hidden name=submit value=1><button id=g>Go</button></form>
<script>document.getElementById('b').addEventListener('pointerdown', () => document.getElementById('g').click());</script>"""


def test_plain_touch_window_hijacked_by_pointerdown():
    from test_rev477_bypasses import _press
    with plain({START: HIJACK} | ALWAYS) as (page, drive, site):
        _press("plain code's Next", page, drive)
        _settle(page, 2500)
        print("bodies", site.bodies)
    assert site.applications() == []


def test_cdp_trusted_press_hijacked_by_pointerdown():
    """Control on CDP: the page's click is untrusted there, so it never counts."""
    from test_rev477_bypasses import _press
    with cdp({START: HIJACK} | ALWAYS) as (page, drive, site):
        _press("plain code's Next", page, drive)
        _settle(page, 2500)
    assert site.applications() == []


# --- KAN-725's vouched Apply

def test_tal_page_vouches_for_itself_with_the_stolen_token():
    from test_submit_guard import _press_tal_apply
    steal = STEAL.replace("{lift: {}}", "{start: true}").replace("<script>", "<script>setInterval(() => {", 1).replace("</script>", "}, 50);</script>", 1)
    posts, blocked = _press_tal_apply(page=steal, start=False, rehearsal=True)
    assert posts == [] and blocked


# A live run's page opened by code that skips on_open: its drive guard is the block-only copy, put in after the page's
# code, which takes no lift or allowance from anyone, the page's forged events and Apply's own alike.
POSTED = "/acme/jobs/123/posted"


@pytest.mark.parametrize("apply_lifts", [False, True], ids=["page lifts", "Apply lifts"])
def test_a_page_opened_without_on_open_gets_a_drive_guard_that_only_blocks(apply_lifts):
    from playwright.sync_api import sync_playwright
    from test_submit_guard_hostile import HOST, Site

    from apply.submit_guard import DriveGuard

    site = Site({START: f"""<title>Jobs</title><form id=go method=post action="{POSTED}"><input type=hidden name=a value=1>
                 </form><script>document.getElementById('go').submit();</script>""",
                 POSTED: f"<title>Apply</title>{FORM}" + HOOK} | ALWAYS)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        context.route(lambda url: True, site.handle)
        page = context.new_page()
        page.goto(HOST + START)
        page.wait_for_url("**" + POSTED)
        drive = DriveGuard(page)
        drive.arm()
        if apply_lifts:
            drive.lift()
        _settle(page, 600)
        try:
            page.locator("#s").click(timeout=2000)
        except Exception:
            pass
        _settle(page, 1000)
        blocked = drive.blocked()
        browser.close()
    assert site.applications() == [] and blocked


# The page's own click handler on the vouched Apply posts a copy with the same entries into a frame of its own,
# again and again: each passes startPost, and the one-post mark is set only by a navigate in the top window.
MANY = """<iframe name=sink></iframe><script>addEventListener('load', () => document.getElementById('go').addEventListener('click', () => {
  const f = document.getElementById('go').form;
  for (let i = 0; i < 3; i++) {
    const c = document.createElement('form'); c.method = 'post'; c.action = f.action; c.target = 'sink';
    c.innerHTML = '<input type=hidden name=__vxXSRF_Token value=t>'; document.body.append(c);
    HTMLFormElement.prototype.submit.call(c);
  }
}));</script>"""


def test_the_vouched_apply_sends_one_post():
    from test_submit_guard import _press_tal_apply
    posts, blocked = _press_tal_apply(page=MANY, rehearsal=True)
    print(posts, blocked)
    assert len(posts) <= 1


# A hidden field whose name says token but also says send: never part of the Apply's token-only form.
@pytest.mark.parametrize("name", ["finalSubmitToken", "submit_token", "applyNonce"])
def test_a_token_named_field_that_says_send_keeps_the_apply_blocked(name):
    from test_submit_guard import _press_tal_apply
    posts, blocked = _press_tal_apply(fields=f'<input type="hidden" name="{name}" value="1">', rehearsal=True)
    assert posts == [] and blocked


# --- other windows
OTHER = {
    "fetch from a new popup's window": f"""<title>Apply</title><button id=b>Open</button><script>
      document.getElementById('b').onclick = () => {{ const w = window.open(''); w.fetch('{FINAL}', {{method: 'POST', body: 'x'}}).catch(() => {{}}); }};</script>""",
    "form post from a new popup's document": f"""<title>Apply</title><button id=b>Open</button><script>
      document.getElementById('b').onclick = () => {{ const w = window.open(''); w.document.body.innerHTML =
        '<form id=f method=post action="{FINAL}"><input name=first value=Test></form>';
        w.HTMLFormElement.prototype.submit.call(w.document.getElementById('f')); }};</script>""",
    "XHR from a srcdoc frame made by script": f"""<title>Apply</title><button id=b>Open</button><script>
      document.getElementById('b').onclick = () => {{ const i = document.createElement('iframe'); i.srcdoc = 'x';
        document.body.append(i); i.onload = () => {{ const x = new i.contentWindow.XMLHttpRequest(); x.open('POST', '{FINAL}'); x.send('a'); }}; }};</script>""",
    "data: URL popup posting": f"""<title>Apply</title><button id=b>Open</button><script>
      document.getElementById('b').onclick = () => {{ const w = window.open('about:blank', 'x');
        const f = document.createElement('form'); f.method = 'post'; f.action = '{FINAL}'; f.target = 'x';
        f.innerHTML = '<input name=first value=Test>'; document.body.append(f); f.requestSubmit(); }};</script>""",
}


@pytest.mark.parametrize("name", list(OTHER))
def test_other_window(name):
    with cdp({START: OTHER[name]} | ALWAYS) as (page, _, site):
        try:
            page.locator("#b").click(timeout=3000)
        except Exception:
            pass
        _settle(page, 1500)
    assert site.applications() == []


# Ashby's submit named only in its body (FINAL_BODIES): fetch reads a Blob body, XHR and sendBeacon don't.
GQL = "https://jobs.ashbyhq.com/api/non-user-graphql"
BODY = '{"operationName":"ApiSubmitSingleApplicationFormAction","variables":{}}'
ASHBY = {
    "CONTROL fetch with a string body": f"""<script>fetch('{GQL}', {{method: 'POST', body: '{BODY}'}}).catch(() => {{}});</script>""",
    "CONTROL fetch with a Blob body": f"""<script>fetch('{GQL}', {{method: 'POST', body: new Blob(['{BODY}'])}}).catch(() => {{}});</script>""",
    "XHR with a Blob body": f"""<script>const x = new XMLHttpRequest(); x.open('POST', '{GQL}'); x.send(new Blob(['{BODY}']));</script>""",
    "sendBeacon with a Blob body": f"""<script>navigator.sendBeacon('{GQL}', new Blob(['{BODY}'], {{type: 'text/plain'}}));</script>""",
    "XHR with an ArrayBuffer body": f"""<script>const x = new XMLHttpRequest(); x.open('POST', '{GQL}'); x.send(new TextEncoder().encode('{BODY}'));</script>""",
}


@pytest.mark.parametrize("name", list(ASHBY))
def test_ashby_body(name):
    with cdp({START: "<title>Apply</title>" + ASHBY[name]} | ALWAYS) as (page, _, site):
        site.sent.clear(); site.bodies.clear()  # the fixture's first load was unguarded
        page.reload()
        _settle(page, 1500)
        print("BLOCKED", page.evaluate("JSON.stringify([window.__applyRehearsalBlocked, window.__applyDriveBlocked])"), site.bodies)
    assert [p for p, b in site.bodies if "ApiSubmit" in b] == []
