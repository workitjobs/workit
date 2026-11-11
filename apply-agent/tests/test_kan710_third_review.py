"""PR 477's third adversarial review (KAN-710): each test is a way a page tried to send past the guards, and each must
send nothing. A CONTROL case is the same page without the trick."""

import pytest
from test_submit_guard_hostile import FINAL, HOST, START, _settle, cdp

from apply import claude_fill, submit_guard
from apply.submit_guard import DriveGuard

OTHER = "https://forms.example.net"  # another site: a cross-site (out-of-process) frame
STEP2 = "/acme/jobs/123/step2"


class Site:
    def __init__(self, pages):
        self.pages, self.sent = pages, []

    def handle(self, route):
        r = route.request
        url = r.url.split("?")[0]
        if r.method not in ("GET", "HEAD", "OPTIONS"):
            self.sent.append((url, r.post_data or ""))
        for prefix in (HOST, OTHER):
            if url.startswith(prefix) and url[len(prefix):] in self.pages.get(prefix, {}):
                return route.fulfill(body=self.pages[prefix][url[len(prefix):]], content_type="text/html")
        route.fulfill(body="<title>Thanks</title>", content_type="text/html")

    def finals(self):
        return [u for u, _ in self.sent if u.endswith("/apply")]


@pytest.fixture(autouse=True)
def quick_steps(monkeypatch):
    monkeypatch.setattr(claude_fill, "STEP_SHOWS_MS", 1500)


def live(pages, before=None, after=None, wait=2500, opened=True):
    """A live run's page: on_open, load, DriveGuard + arm (Claude fill's first drive), then `after`."""
    from playwright.sync_api import sync_playwright
    site = Site(pages)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        context.route(lambda url: True, site.handle)
        page = context.new_page()
        if opened:
            submit_guard.on_open(page)
        page.goto(HOST + START)
        _settle(page, 800)
        if before:
            before(page)
        drive = DriveGuard(page)
        drive.arm()
        _settle(page, 300)
        if after:
            after(page, drive)
        _settle(page, wait)
        blocked = drive.blocked()
        browser.close()
    print("sent:", site.sent, "blocked:", blocked)
    return site, blocked


FORM = f'<form id=f method=post action="{FINAL}"><input name=first value=Test><button id=s>Submit application</button></form>'


# A cross-site frame on a live run's page: on_open's copy there starts lifted; does arm() reach it?
def test_cross_site_frame_stays_lifted_fetch():
    frame = f"<script>setTimeout(() => fetch('{OTHER}/x/apply', {{method: 'POST', body: 'a'}}).catch(() => {{}}), 1800);</script>"
    site, _ = live({HOST: {START: f"<title>Apply</title><iframe src='{OTHER}/frame'></iframe>"}, OTHER: {"/frame": frame}})
    assert site.finals() == []


def test_cross_site_frame_claudes_click_on_submit():
    frame = f'<form method=post action="{OTHER}/x/apply"><input name=a value=1><button id=s>Submit application</button></form>'

    def click(page, drive):
        try:
            page.frame_locator("iframe").locator("#s").click(timeout=2000)
        except Exception as e:
            print("click", e)
    site, _ = live({HOST: {START: f"<title>Apply</title><iframe src='{OTHER}/frame'></iframe>"}, OTHER: {"/frame": frame}},
                   after=click)
    assert site.finals() == []


# A same-origin frame whose document the page swaps in right as arm() runs: no proof, a probe for a race.
RACE = f"""<title>Apply</title><iframe id=i src='{HOST}{STEP2}'></iframe><script>
  let n = 0; const i = document.getElementById('i');
  const t = setInterval(() => {{ i.src = '{HOST}{STEP2}?' + (n++); }}, 5);
  setTimeout(() => clearInterval(t), 1500);
  setTimeout(() => {{ for (const f of window.frames) try {{ f.fetch('{FINAL}', {{method: 'POST', body: 'r'}}).catch(() => {{}}); }} catch (e) {{}} }}, 2500);
</script>"""


def test_frame_swapped_during_arm():
    site, _ = live({HOST: {START: RACE, STEP2: "<title>F</title>"}}, wait=3500)
    assert site.finals() == []


# XHR's open and send are each patched per realm, and send looks up what open saw in its own realm's WeakMap: an
# XHR opened by another realm's open (a same-origin frame's) is unknown to this realm's send, which read it as a GET
# (fixed by KAN-783: it is not sent). Ashby's submit in form data, by XHR or beacon, went unread.
GQL = "https://jobs.ashbyhq.com/api/non-user-graphql"
BODY = '{"operationName":"ApiSubmitSingleApplicationFormAction","variables":{}}'
CROSS = {
    "XHR opened by a frame's open, sent by the page's send": f"""<title>Apply</title><iframe id=i></iframe><script>
      setTimeout(() => {{ const x = new XMLHttpRequest();
        document.getElementById('i').contentWindow.XMLHttpRequest.prototype.open.call(x, 'POST', '{FINAL}');
        x.send('first=Test'); }}, 300);</script>""",
    "XHR opened by the page's open, sent by a frame's send": f"""<title>Apply</title><iframe id=i></iframe><script>
      setTimeout(() => {{ const x = new XMLHttpRequest(); x.open('POST', '{FINAL}');
        document.getElementById('i').contentWindow.XMLHttpRequest.prototype.send.call(x, 'first=Test'); }}, 300);</script>""",
    "Ashby submit in a FormData body over XHR": f"""<title>Apply</title><script>
      const fd = new FormData(); fd.append('operations', '{BODY}');
      const x = new XMLHttpRequest(); x.open('POST', '{GQL}'); x.send(fd);</script>""",
    "Ashby submit in a FormData body by beacon": f"""<title>Apply</title><script>
      const fd = new FormData(); fd.append('operations', '{BODY}'); navigator.sendBeacon('{GQL}', fd);</script>""",
}


CROSS["CONTROL XHR opened and sent by the page's own"] = f"""<title>Apply</title><script>
  setTimeout(() => {{ const x = new XMLHttpRequest(); x.open('POST', '{FINAL}'); try {{ x.send('first=Test'); }} catch (e) {{}} }}, 300);</script>"""
CROSS["CONTROL Ashby submit in a string body over XHR"] = f"""<title>Apply</title><script>
  const x = new XMLHttpRequest(); x.open('POST', '{GQL}'); try {{ x.send('{BODY}'); }} catch (e) {{}}</script>"""


@pytest.mark.parametrize("name", list(CROSS))
def test_rehearsal_cross_realm(name):
    """A rehearsal on a CDP Worker: its guard on before the page's code (reloaded), its route below."""
    with cdp({START: CROSS[name], "/acme/jobs/123/step2": "x"}) as (page, _, site):
        site.sent.clear(); site.bodies.clear()
        page.reload()
        _settle(page, 1500)
        print("sent", site.sent, site.bodies)
    assert site.applications() == [] and [p for p, b in site.bodies if "ApiSubmit" in b] == []


@pytest.mark.parametrize("name", list(CROSS))
def test_plain_cross_realm(name):
    from test_submit_guard_hostile import plain
    with plain({START: CROSS[name], "/acme/jobs/123/step2": "x"}) as (page, _d, site):
        site.sent.clear(); site.bodies.clear()
        page.reload()
        _settle(page, 2000)
        print("sent", site.sent, site.bodies)
    assert site.applications() == [] and [p for p, b in site.bodies if "ApiSubmit" in b] == []


# A frame with scripts off (sandbox without allow-scripts) runs no init script, so no guard; but its parent may
# still call that frame's realm's fetch, XHR and beacon, which nothing patched.
SANDBOX = {
    "fetch from a no-scripts frame's realm": f"""<title>Apply</title><iframe id=i sandbox="allow-same-origin" srcdoc="<p>x"></iframe><script>
      setTimeout(() => document.getElementById('i').contentWindow.fetch('{FINAL}', {{method: 'POST', body: 'first=Test'}}).catch((e) => console.log('E', e)), 300);</script>""",
    "XHR from a no-scripts frame's realm": f"""<title>Apply</title><iframe id=i sandbox="allow-same-origin" srcdoc="<p>x"></iframe><script>
      setTimeout(() => {{ const w = document.getElementById('i').contentWindow; const x = new w.XMLHttpRequest();
        x.open('POST', '{FINAL}'); x.send('first=Test'); }}, 300);</script>""",
    "beacon from a no-scripts frame's realm": f"""<title>Apply</title><iframe id=i sandbox="allow-same-origin" srcdoc="<p>x"></iframe><script>
      setTimeout(() => document.getElementById('i').contentWindow.navigator.sendBeacon('{FINAL}', 'first=Test'), 300);</script>""",
    "form submit() of the page's form by a no-scripts frame's submit": f"""<title>Apply</title><iframe id=i sandbox="allow-same-origin allow-forms" srcdoc="<p>x"></iframe>
      <form id=f method=post action="{FINAL}"><input name=first value=Test></form><script>
      setTimeout(() => document.getElementById('i').contentWindow.HTMLFormElement.prototype.submit.call(document.getElementById('f')), 300);</script>""",
}


@pytest.mark.parametrize("name", list(SANDBOX))
def test_rehearsal_sandboxed_realm(name):
    with cdp({START: SANDBOX[name]}) as (page, _, site):
        site.sent.clear(); site.bodies.clear()
        page.reload()
        _settle(page, 1500)
        print("sent", site.sent)
    assert site.applications() == []


@pytest.mark.parametrize("name", list(SANDBOX))
def test_plain_sandboxed_realm(name):
    from test_submit_guard_hostile import plain
    with plain({START: SANDBOX[name]}) as (page, _d, site):
        site.sent.clear(); site.bodies.clear()
        page.reload()
        _settle(page, 2000)
        print("sent", site.sent)
    assert site.applications() == []


# Live run, after arm: a new about:blank popup's realm, and a frame's.
AFTER = {
    "about:blank popup fetch": f"""<title>Apply</title><script>setTimeout(() => {{ const w = window.open('');
       w.fetch('{FINAL}', {{method: 'POST', body: 'x'}}).catch(() => {{}}); }}, 1500);</script>""",
    "about:blank popup XHR": f"""<title>Apply</title><script>setTimeout(() => {{ const w = window.open('');
       const x = new w.XMLHttpRequest(); x.open('POST', '{FINAL}'); try {{ x.send('x'); }} catch (e) {{}} }}, 1500);</script>""",
    "new about:blank frame XHR": f"""<title>Apply</title><script>setTimeout(() => {{ const i = document.createElement('iframe');
       document.body.append(i); const x = new i.contentWindow.XMLHttpRequest(); x.open('POST', '{FINAL}'); try {{ x.send('x'); }} catch (e) {{}} }}, 1500);</script>""",
    "cross-realm XHR (frame open, page send)": f"""<title>Apply</title><iframe id=i></iframe><script>setTimeout(() => {{ const x = new XMLHttpRequest();
       document.getElementById('i').contentWindow.XMLHttpRequest.prototype.open.call(x, 'POST', '{FINAL}'); x.send('x'); }}, 1500);</script>""",
}


@pytest.mark.parametrize("name", list(AFTER))
def test_live_after_arm(name):
    site, _ = live({HOST: {START: AFTER[name]}}, wait=2500)
    assert site.finals() == []


# A popup the page opened before Claude fill's DriveGuard: on_open's copy there is lifted, and arm() goes only to
# the driven page's frames.
POPUP_EARLY = f"""<title>Apply</title>{FORM}<script>
  window.w = window.open('{HOST}{STEP2}', 'side');
  setTimeout(() => window.w.fetch('{FINAL}', {{method: 'POST', body: 'first=Test'}}).catch(() => {{}}), 2000);
</script>"""


def test_popup_opened_before_arm_fetch():
    site, _ = live({HOST: {START: POPUP_EARLY, STEP2: "<title>Side</title>"}})
    assert site.finals() == []


def test_popup_opened_before_arm_own_script():
    side = f"<title>Side</title><script>setTimeout(() => fetch('{FINAL}', {{method: 'POST', body: 'x'}}).catch(() => {{}}), 2000);</script>"
    site, _ = live({HOST: {START: f"<title>Apply</title><script>window.open('{HOST}{STEP2}', 'side');</script>",
                           STEP2: side}})
    assert site.finals() == []


def test_popup_opened_before_arm_form_post_from_opener():
    page_ = f"""<title>Apply</title><script>
      const w = window.open('{HOST}{STEP2}', 'side');
      setTimeout(() => {{ const d = w.document; const f = d.createElement('form'); f.method = 'post'; f.action = '{FINAL}';
        f.innerHTML = '<input name=first value=Test>'; d.body.append(f); w.HTMLFormElement.prototype.submit.call(f); }}, 2000);
    </script>"""
    site, _ = live({HOST: {START: page_, STEP2: "<title>Side</title><body></body>"}})
    assert site.finals() == []


# A target=_blank form post the page aims into a window it opened before arm, from the armed page: judged by the
# armed opener's guard.
def test_form_into_lifted_popup():
    page_ = f"""<title>Apply</title><script>window.open('{HOST}{STEP2}', 'side');
      setTimeout(() => {{ const w = window.open('', 'side'); w.eval("fetch('{FINAL}', {{method:'POST', body:'q'}})"); }}, 2000);</script>"""
    site, _ = live({HOST: {START: page_, STEP2: "<title>Side</title>"}})
    assert site.finals() == []


# A plain Worker's drive guard is one registration ("drive") for the whole Worker, every tab. A second form's
# on_open on the same Worker (a live run sent in with --into while another is open) puts on_open's lifted copy in its
# place, for the first form's tab too; PlainDriveGuard arms the open document by the control only, so the first
# form's next page, driven by Claude, has a lifted drive guard.
NEXT_PAGE = f"<title>Step two</title><script>setTimeout(() => fetch('{FINAL}', {{method: 'POST', body: 'first=Test'}}).catch(() => {{}}), 800);</script>"


@pytest.mark.parametrize("second", [False, True], ids=["CONTROL one form", "a second form's on_open"])
def test_plain_second_on_open_lifts_the_first_forms_drive_guard(second):
    from test_submit_guard_hostile import Site as HSite
    from test_submit_guard_hostile import _plain_or_skip
    _plain_or_skip()
    from plain_fakes import _shared, fake_page

    from apply.plain import guards
    from apply.plain.page import PortContext
    guards.reset(_shared().connection)
    site = HSite({START: "<title>Apply</title><a id=n href='/acme/jobs/123/step2'>Next</a>", STEP2: NEXT_PAGE})
    with fake_page(site.handle) as page:
        submit_guard.on_open(page)  # a live run's tab
        page.goto(HOST + START)
        drive = DriveGuard(page)
        drive.arm()
        if second:
            other = PortContext(page.worker).new_page()
            submit_guard.on_open(other)  # the second form's tab, before its first load
        page.goto(HOST + STEP2)  # Claude's Next on the first form
        _settle(page, 2000)
        print("sent", site.sent, "blocked", drive.blocked())
    assert site.applications() == []


# The noted rehearsal residual, carried across documents: a page that heard the drive guard's control name in one
# document (the full copy put in after its code) keeps it (sessionStorage) and lifts the drive guard in every later
# document, whose copy ran first. Claude's click on "Delete my account" then goes (the rehearsal's guard lets a
# non-final fetch through).
DEL = "/acme/account/delete"
HEAR = """<script>
const add = EventTarget.prototype.addEventListener;
EventTarget.prototype.addEventListener = function (type, ...rest) {
  if (/^__applyDriveControl[0-9a-f]{32}$/.test(String(type))) sessionStorage.t = String(type);
  return add.call(this, type, ...rest);
};</script>"""
LATER = f"""<title>Account</title><script>
if (sessionStorage.t) dispatchEvent(new CustomEvent(sessionStorage.t, {{detail: JSON.stringify({{lift: {{}}}})}}));
</script><button id=d onclick="fetch('{DEL}', {{method: 'POST', body: 'x'}})">Delete my account</button>"""


@pytest.mark.parametrize("steal", [False, True], ids=["CONTROL no theft", "token kept from the first document"])
def test_rehearsal_drive_token_carried_to_later_documents(steal):
    with cdp({START: "<title>Apply</title>" + (HEAR if steal else ""), STEP2: LATER}) as (page, drive, site):
        drive.arm()
        page.goto(HOST + STEP2)
        _settle(page, 500)  # Claude drives on: no arm() between its steps
        try:
            page.locator("#d").click(timeout=2000)
        except Exception:
            pass
        _settle(page, 1000)
        print("sent", site.sent, "blocked", drive.blocked())
    assert DEL not in site.sent
