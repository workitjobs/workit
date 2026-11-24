"""WorkIt Auto Apply's window (KAN-723, W5 of docs/desktop_application_auto_apply.md; D11, D12): one native window
(pywebview: WKWebView on a Mac) and no port.

The app's window shows the student page (KAN-867: window/, built into STUDENT_PAGE); a window that can start no run
(a Developer checkout's) shows the Apply window's own page (apply.dashboard's). Either is served by no server:
Dashboard(serve=False) listens on nothing, and SHIM, put in the page before its scripts, sends the page's requests to `Bridge`, pywebview's
JavaScript bridge (js_api), which answers each one in this process through the same routes, checks and token as
the server (Dashboard.respond). The tiles' frames come from Bridge.frames as the server's /frames stream would; a
link to a file a tile lists opens in the system's own app.

Signed out, the window first shows SIGN_IN: Sign In with WorkIt opens WorkIt's /app-sign-in page in the default
browser with this sign-in's PKCE challenge (workit.pkce). The page's Open WorkIt Auto Apply opens its
workit-auto-apply:// link, which the window takes and trades by itself: the built app claims the link (W8), and a
checkout's window has a helper app claim it for it (apply.sign_in_link). Where there is no helper, the code is pasted
in the box, which only WorkIt's admins' page shows.
Then Bridge.trade signs in (WorkIt.trade). Next comes FIRST_RUN while any first-run step is left (apply.first_run:
Chrome, the disclosure and license, Screen Recording, the seed), then the Apply window.

A run (W5 step 4): with no run going, the student page shows Find jobs, the student's best matches to pick from
(Bridge.matches, KAN-882), and a step away the student's Auto Apply queue on WorkIt (Bridge.queue), a box to paste
one posting's link and Start (Bridge.start), and says when today's model use nears the
Usage cap (Bridge.usage). Start hands the links to `start` (apply.student.Runs), which rehearses them in the Workers
and shows the run's own board, till every form it held is closed; then the window shows the idle board again. The
page reads its board's state through the routes (/state) either way. A run that can't start (no engine, W7; a Worker
profile in use) says why in one line (Bridge.status).

The app's pages load no web font: Google Fonts would be a request the privacy page doesn't name (FONTS). The
student page carries its own Inter.

Settings (W5 step 5) has Report a problem (D26, apply.report): the form's answers make a report (review_report),
the window shows what it holds, and Send Report sends that same report (send_report). An Application's card sends
its Application's id with the same call, for its record and log; its Send Report sends that id too, so a report
another form reviewed since is never the one that goes.

pywebview gives the page every public method of Bridge, and nothing whose name starts with "_".
"""

import base64
import html
import json
import os
import re
import signal
import sys
import threading
import time
import webbrowser
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlencode

from apply import first_run, report, sign_in_link, updates, workit
from apply.adapters import SetupError
from apply.dashboard import FRAME_GAP, QUEUED_JOB, Dashboard
from apply.dashboard_page import STYLE
from apply.first_run import CHROME_DOWNLOAD, EULA, NOTICES, READY, FirstRun
from apply.home import HOME
from apply.model import Status
from apply.tracker import FileTracker, Row

TITLE = "WorkIt Auto Apply"
# The student page, built from window/ by Vite (`npm run build`) into one file: CI checks it matches its source.
STUDENT_PAGE = Path(__file__).with_name("student_page") / "index.html"
# The Applicant profile's file, whose values a report's log is masked with (apply.report.build): never its folder.
PROFILE = HOME / "applicant-profile.yaml"
# How long Bridge.frames waits for a new frame before it answers none, so the page asks again.
FRAMES_WAIT = 1.0
# The Apply window's web font links, left out of the app's page: the system's fonts stand in.
FONTS = re.compile(r'<link[^>]+fonts\.googleapis\.com[^>]*>')
READY_JS = """const ready = new Promise(done => (window.pywebview && window.pywebview.api) ? done()
                                   : addEventListener('pywebviewready', () => done(), {once: true}));"""


def _light(style: str) -> str:
    """The Apply window's style without its dark scheme: the student page is light only, so the app's own pages
    (sign-in, first run, Settings) stay light too, and the window never turns dark between them."""
    start = style.find("@media (prefers-color-scheme: dark)")
    if start < 0:
        return style
    depth = 0
    for at in range(style.index("{", start), len(style)):
        depth += {"{": 1, "}": -1}.get(style[at], 0)
        if not depth:
            return style[:start] + _light(style[at + 1:])
    return style


APP_STYLE = _light(STYLE)

# The page's requests through the bridge (D11): fetch of a path, the /frames stream, the close beacon, a file link.
SHIM = r"""<script>
(() => {
  const ready = new Promise(done => (window.pywebview && window.pywebview.api) ? done()
                                     : addEventListener('pywebviewready', () => done(), {once: true}));
  const bytes = text => Uint8Array.from(atob(text), c => c.charCodeAt(0));
  const asked = (input, init) => ({url: typeof input === 'string' ? input : input.url,
    method: ((init && init.method) || 'GET').toUpperCase(),
    headers: Object.fromEntries(new Headers((init && init.headers) || {})),
    body: init && init.body != null ? String(init.body) : ''});
  // /frames as the server streams it: (tile, length) in two big-endian words, then the JPEG.
  const frames = () => { const seen = {}; return new Response(new ReadableStream({async pull(into) {
    await ready;
    for (const f of await window.pywebview.api.frames(seen)) {
      seen[f.tile] = f.number;
      const jpeg = bytes(f.jpeg), head = new Uint8Array(8), view = new DataView(head.buffer);
      view.setUint32(0, f.tile); view.setUint32(4, jpeg.length);
      into.enqueue(head); into.enqueue(jpeg);
    }
  }})); };
  const original = window.fetch.bind(window);
  window.fetch = async (input, init) => {
    const request = asked(input, init);
    if (!request.url.startsWith('/')) return original(input, init);
    if (request.url === '/frames') return frames();
    await ready;
    const got = await window.pywebview.api.request(request.method, request.url, request.headers, request.body);
    const none = [204, 205, 304].includes(got.status);
    return new Response(none ? null : (got.base64 ? bytes(got.body) : got.body),
                        {status: got.status, headers: {'Content-Type': got.type}});
  };
  navigator.sendBeacon = () => true;  // the window's own close ends the app (app_window.run)
  document.addEventListener('click', async event => {
    const link = event.target.closest && event.target.closest('a[href^="/"]');
    if (!link) return;
    event.preventDefault();
    await ready;
    window.pywebview.api.open(link.getAttribute('href'));
  }, true);
})();
</script>"""

SIGN_IN = """<!doctype html><meta charset="utf-8"><title>WorkIt Auto Apply</title>
<meta name="color-scheme" content="light"><style>{style}
  main.signin { max-width: 26rem; margin: 18vh auto; display: flex; flex-direction: column; gap: 0.9rem; }
  main.signin input { width: 100%; box-sizing: border-box; }
</style>
<main class="signin">
<h1>Sign In to WorkIt Auto Apply</h1>
<p>Sign in with your WorkIt account in your browser. WorkIt Auto Apply finishes signing in when you come back.</p>
<button class="primary" id="start">Sign In with WorkIt</button>
<form id="code" hidden><label>If WorkIt's page shows a code, paste it here
<input id="pasted" autocomplete="off" spellcheck="false"></label><button class="primary">Continue</button></form>
<p id="said" role="status"></p>
</main>
<script>
{ready}
const said = document.getElementById('said'), form = document.getElementById('code');
let poll;
document.getElementById('start').addEventListener('click', async () => {
  await ready;
  clearInterval(poll);
  await window.pywebview.api.sign_in();
  form.hidden = false;
  said.textContent = 'Sign in on the WorkIt page that opened in your browser, then press Open WorkIt Auto Apply.';
  // The page's link comes back through the helper (apply.sign_in_link): the window signs in by itself.
  poll = setInterval(async () => {
    const got = await window.pywebview.api.take_link();
    if (got.error) { clearInterval(poll); said.textContent = got.error; }
  }, 1000);
});
form.addEventListener('submit', async event => {
  event.preventDefault();
  said.textContent = 'Signing in…';
  const got = await window.pywebview.api.trade(document.getElementById('pasted').value);
  if (got.error) said.textContent = got.error;
});
</script>""".replace("{style}", APP_STYLE).replace("{ready}", READY_JS)

# What leaves the computer (section 3.4, /privacy): first run and Settings show it.
DISCLOSURE = """<ul>
<li><b>To WorkIt:</b> what each AI call needs, without your private details such as your contact details, street
address and self-identification answers; your applications' stages; the answers you approve; your Auto Apply queue.
One application's record and log go only when you press Send Report.</li>
<li><b>To Groq and Google (Gemini):</b> the same AI prompts, sent by WorkIt with WorkIt's own key. Google's free
tier may use the prompts and answers it gets to improve its products, and people at Google may read them.</li>
<li><b>To job sites:</b> your answers, typed into each form as you would type them.</li>
<li><b>To Brandfetch:</b> the website of each company in your queue, to show its logo, as WorkIt's website does.
Without one there, the logo comes from the company's job board or Google's website icons the same way.</li>
</ul>
<p>The records of each application, the Chrome windows' profiles and sign-ins, and your job-site passwords (in the
Keychain) stay on your Mac. WorkIt Auto Apply never presses Submit: you do.</p>"""

FIRST_RUN = """<!doctype html><meta charset="utf-8"><title>WorkIt Auto Apply</title>
<meta name="color-scheme" content="light"><style>{style}
  main.first { max-width: 34rem; margin: 12vh auto; display: flex; flex-direction: column; gap: 0.9rem; }
  main.first section { display: flex; flex-direction: column; gap: 0.8rem; }
  main.first .row { display: flex; gap: 0.6rem; flex-wrap: wrap; }
  main.first pre { white-space: pre-wrap; max-height: 16rem; overflow: auto; font: inherit; }
</style>
<main class="first">
<section id="chrome" hidden>
<h1>WorkIt Auto Apply Needs Google Chrome</h1>
<p>It fills each form in a Chrome window of its own, never in your own Chrome profiles.
WorkIt Auto Apply goes on by itself once Chrome is installed.</p>
<div class="row"><button class="primary" data-do="get_chrome">Download Google Chrome</button></div>
</section>
<section id="disclosure" hidden>
<h1>What Leaves Your Mac</h1>
{disclosure}
<p>By pressing OK you agree to WorkIt Auto Apply's license.</p>
<div class="row"><button class="primary" data-do="accept_disclosure">OK</button>
<button data-do="show_license">Read the License</button></div>
</section>
<section id="screen" hidden>
<h1>Allow Screen Recording</h1>
<p>WorkIt Auto Apply shows each form live in its window, so you can fix it there. With Screen Recording on, that
view is smooth; without it, it shows about two frames a second. macOS asks you once, and System Settings keeps the
switch (Privacy &amp; Security, Screen &amp; System Audio Recording).</p>
<div class="row"><button class="primary" data-do="allow_screen">Allow</button>
<button data-do="skip_screen">Not Now</button></div>
</section>
<section id="seed" hidden>
<h1>Set Up the Worker Extension</h1>
<p>WorkIt Auto Apply opens Chrome on a profile of its own. There you turn on Developer mode and load the Worker
extension's folder; WorkIt Auto Apply watches, then checks one Worker. It takes about a minute.</p>
<div class="row"><button class="primary" id="seed-start" data-do="start_seed">Set Up</button>
<button id="seed-again" data-do="seed_again" hidden>Try Again</button></div>
<pre id="seed-lines" role="log"></pre>
<p id="seed-failed" role="alert"></p>
</section>
</main>
<script>
{ready}
let going = false;
const show = state => {
  for (const section of document.querySelectorAll('section')) section.hidden = section.id !== state.step;
  if (state.step === 'ready' && !going) { going = true; window.pywebview.api.go_on(); return; }
  document.getElementById('seed-lines').textContent = state.lines.join('\\n');
  document.getElementById('seed-start').hidden = state.running;
  document.getElementById('seed-again').hidden = !state.waiting;
  document.getElementById('seed-failed').textContent = state.failed;
};
document.addEventListener('click', async event => {
  const button = event.target.closest('button[data-do]');
  if (!button) return;
  await ready;
  show(await window.pywebview.api[button.dataset.do]());
});
ready.then(async () => {
  show(await window.pywebview.api.first_run());
  setInterval(async () => show(await window.pywebview.api.first_run()), 1500);  // Chrome installed, the seed's steps
});
</script>""".replace("{style}", APP_STYLE).replace("{ready}", READY_JS).replace("{disclosure}", DISCLOSURE)

SETTINGS = """<!doctype html><meta charset="utf-8"><title>WorkIt Auto Apply</title>
<meta name="color-scheme" content="light"><style>{style}
  main.settings { max-width: 34rem; margin: 8vh auto; display: flex; flex-direction: column; gap: 0.8rem; }
  main.settings .row { display: flex; gap: 0.6rem; flex-wrap: wrap; }
  main.settings .top { justify-content: space-between; align-items: center; }
</style>
<main class="settings">
<div class="row top"><h1>Settings</h1><button data-do="back">Back</button></div>
<label>Workers at once <select id="workers"><option>1</option><option>2</option><option>3</option></select></label>
<p>Each Worker is a full Chrome, about 0.5 to 1 GB of memory. The next Start uses the new count.</p>
<div class="row"><button id="show-disclosure">What Leaves Your Mac</button>
<button data-do="show_license">Read the License</button>
<button data-do="show_notices" id="notices" hidden>Third-Party Notices</button></div>
<div id="disclosure" hidden>{disclosure}</div>
<h2>Report a Problem</h2>
<form id="report">
<label>What is it about <select id="report-category">{categories}</select></label>
<label>What happened <textarea id="report-note" rows="4" maxlength="2000" style="width: 100%"></textarea></label>
<label><input type="checkbox" id="report-contact"> WorkIt may email me about this</label>
<div class="row"><button>Review Report</button></div>
</form>
<div id="report-review" hidden><p>What goes to WorkIt, and nothing else:</p><ul id="report-parts"></ul>
<div class="row"><button class="primary" id="report-send">Send Report</button></div></div>
<p id="report-said" role="status"></p>
<div class="row"><button data-do="sign_out">Sign Out</button></div>
<p>Remove All My Data deletes everything WorkIt Auto Apply keeps on this Mac: the Worker profiles and their
sign-ins, the seed, the records and logs of your applications, and its WorkIt sign-in. Your WorkIt account stays.</p>
<div class="row"><button id="remove">Remove All My Data</button>
<button id="remove-sure" data-do="remove_data" hidden>Press Again to Remove Everything</button></div>
<p id="said" role="status"></p>
<div class="row"><button class="primary" data-do="back">Done</button></div>
</main>
<script>
{ready}
const said = document.getElementById('said'), count = document.getElementById('workers');
document.getElementById('show-disclosure').addEventListener('click', () => {
  const shown = document.getElementById('disclosure'); shown.hidden = !shown.hidden; });
document.getElementById('remove').addEventListener('click', () => { document.getElementById('remove-sure').hidden = false; });
count.addEventListener('change', async () => { await ready; await window.pywebview.api.set_workers(Number(count.value)); });
document.addEventListener('click', async event => {
  const button = event.target.closest('button[data-do]');
  if (!button) return;
  await ready;
  const got = await window.pywebview.api[button.dataset.do]();
  said.textContent = (got && (got.error || got.said)) || '';
});
const report = document.getElementById('report'), review = document.getElementById('report-review');
const reportSaid = document.getElementById('report-said');
report.addEventListener('input', () => { review.hidden = true; });  // a changed answer: Review Report again
report.addEventListener('submit', async event => {
  event.preventDefault();
  await ready;
  const got = await window.pywebview.api.review_report(document.getElementById('report-category').value,
    document.getElementById('report-note').value, document.getElementById('report-contact').checked);
  reportSaid.textContent = got.error || '';
  const parts = document.getElementById('report-parts');
  parts.replaceChildren(...(got.parts || []).map(part => Object.assign(document.createElement('li'), {textContent: part})));
  review.hidden = !got.parts;
});
document.getElementById('report-send').addEventListener('click', async () => {
  await ready;
  const got = await window.pywebview.api.send_report();
  reportSaid.textContent = got.error || got.said;
  if (!got.error) { review.hidden = true; report.reset(); }
});
ready.then(async () => {
  const state = await window.pywebview.api.settings_state();
  count.value = String(state.workers);
  document.getElementById('notices').hidden = !state.notices;
});
</script>""".replace("{style}", APP_STYLE).replace("{ready}", READY_JS).replace("{disclosure}", DISCLOSURE).replace(
    "{categories}", "".join(f'<option value="{key}">{html.escape(words)}</option>' for key, words in report.CATEGORIES.items()))


# The page's charset meta, as the developer page (`<meta charset="utf-8">`) and Vite (`<meta charset="utf-8" />`)
# write it: what goes before the page's scripts is put right after it.
CHARSET = re.compile(r'<meta charset="?utf-8"?\s*/?>', re.IGNORECASE)


def _before_scripts(html: str, inserted: str) -> str:
    """`html` with `inserted` right after its charset meta, before any script; at the very start with none."""
    head = CHARSET.search(html)
    return html[:head.end()] + inserted + html[head.end():] if head else inserted + html


def page(dashboard: Dashboard) -> str:
    """The Apply window's page with SHIM before its scripts and no web font: a Developer checkout's window."""
    return _before_scripts(FONTS.sub("", dashboard.page()), SHIM)


def student_page(dashboard: Dashboard) -> str:
    """The student page (KAN-867: window/, built into STUDENT_PAGE) for `dashboard`'s board, with SHIM and the
    window's token before its scripts: the page reads the token as window.APPLY_TOKEN and sends it with each edit,
    and an Application's Report a problem lists window.REPORT_CATEGORIES (apply.report's, as Settings does)."""
    token = (f"<script>window.APPLY_TOKEN = {json.dumps(dashboard.token)};"
             f" window.REPORT_CATEGORIES = {json.dumps(report.CATEGORIES)};</script>")
    return _before_scripts(STUDENT_PAGE.read_text(encoding="utf-8"), SHIM + token)


class Bridge:
    """What the window's page may call (pywebview's js_api): the Apply window's routes, its frames and files, and
    the sign-in. `open_link` opens a URL in the default browser, or a file in the system's own app."""

    def __init__(self, dashboard: Dashboard, client: workit.WorkIt | None = None,
                 open_link: Callable[[str], object] = webbrowser.open, first_run: FirstRun | None = None,
                 start: Callable[[list[str], Callable[[Dashboard], None]], None] | None = None,
                 remove: Callable[[Callable[[], None]], str] = first_run.remove_all_data, link=sign_in_link,
                 forward: Callable[[], object] = lambda: bring_forward()):
        """`start(links, show)`, when given, runs `links` and calls `show(board)` with the run's own Apply window
        (apply.student.Runs.run); the window then shows the student page."""
        self._dashboard = self._idle = dashboard
        self._client = client or workit.WorkIt()
        self._open_link = open_link
        self._first = first_run or FirstRun()
        self._start = start
        self._remove = remove
        self._link = link  # the sign-in page's link, handed to this window (apply.sign_in_link: ready, clear, take)
        self._forward = forward  # the window brought in front of the browser
        self._running = threading.Event()  # a run is going
        self._said = ""  # why the last run couldn't start or stopped
        self._queued: dict[str, dict] = {}  # each queued job (QUEUED_JOB) by its link, for a run's window (KAN-871)
        self._verifier: str | None = None  # this sign-in's PKCE verifier, till its code is traded
        self._report: dict | None = None  # the report the window showed, till Send Report sends it
        self._window = None  # the pywebview window, once run() made it

    def request(self, method: str, path: str, headers: dict | None = None, body: str = "") -> dict:
        """One of the page's requests, answered as the Apply window's server answers it."""
        status, kind, data = self._dashboard.respond(method, path, {str(k): str(v) for k, v in (headers or {}).items()},
                                                     (body or "").encode())
        text = kind.startswith(("application/json", "text/"))
        return {"status": status, "type": kind, "base64": not text,
                "body": data.decode() if text else base64.b64encode(data).decode()}

    def frames(self, seen: dict | None = None) -> list[dict]:
        """Each tile's frame newer than the number `seen` has for it, waiting up to FRAMES_WAIT for one."""
        numbers = {int(tile): int(number) for tile, number in (seen or {}).items()}
        deadline = time.monotonic() + FRAMES_WAIT
        while not (found := self._dashboard.new_frames(numbers)) and time.monotonic() < deadline:
            time.sleep(FRAME_GAP)
        return [{"tile": tile, "number": number, "jpeg": base64.b64encode(frame).decode()}
                for tile, number, frame in found]

    def open(self, path: str) -> bool:
        """A link of the page's to a file a tile or History lists: opened in the system's own app. Any other path
        opens nothing."""
        listed = self._dashboard.listed(str(path))
        if listed:
            self._open_link(listed.as_uri())
        return listed is not None

    def signed_in(self) -> bool:
        return self._client.logged_in()

    def sign_in(self) -> str:
        """WorkIt's sign-in page in the default browser, for a new sign-in: its URL."""
        self._link.ready()  # before the page opens: its link must find the helper registered
        self._link.clear()
        self._verifier, challenge = workit.pkce()
        url = workit.sign_in_page(self._client.site, challenge)
        self._open_link(url)
        return url

    def trade(self, code: str) -> dict:
        """The code WorkIt's page gave, for a session; then the window shows the Apply window. {email}, or {error}
        with what to do."""
        if self._verifier is None:
            return {"error": "Press Sign In with WorkIt first."}
        try:
            account = self._client.trade(str(code), self._verifier)
        except workit.SignInOver:
            self._verifier = None  # spent: a new sign-in makes a new one
            return {"error": "That code didn't work. Press Sign In with WorkIt again."}
        except workit.WorkItError as error:
            return {"error": f"WorkIt couldn't sign you in ({error}). Try again."}
        self._verifier = None
        if self._window is not None:
            self._window.load_html(self._html())
        return {"email": account.email}

    def take_link(self) -> dict:
        """The sign-in page's link, if the helper was handed it, traded as a pasted code is: {email} or {error};
        {} while there is none (the page asks again each second). The window then comes in front of the browser the
        student pressed Open WorkIt Auto Apply in, signed in or saying why not."""
        if self._verifier is None:
            return {}
        link = self._link.take()
        if not link:
            return {}
        got = self.trade(link)
        self._forward()
        return got

    # First run (apply.first_run): each answers the steps' state, which FIRST_RUN shows.

    def first_run(self) -> dict:
        return self._first.state()

    def get_chrome(self) -> dict:
        self._open_link(CHROME_DOWNLOAD)
        return self._first.state()

    def accept_disclosure(self) -> dict:
        self._first.accept()
        return self._first.state()

    def show_license(self) -> dict:
        self._open_link(EULA.as_uri())
        return self._first.state()

    def allow_screen(self) -> dict:
        self._first.allow_screen()
        return self._first.state()

    def skip_screen(self) -> dict:
        self._first.skip_screen()
        return self._first.state()

    def start_seed(self) -> dict:
        self._first.start_seed()
        return self._first.state()

    def seed_again(self) -> dict:
        self._first.seed_again()
        return self._first.state()

    def go_on(self) -> dict:
        """First run done: the Apply window."""
        state = self._first.state()
        if state["step"] == READY and self._window is not None:
            self._window.load_html(self._page())
        return state

    # A run (W5 step 4).

    def queue(self) -> list[dict] | dict:
        """The student's queued, open jobs on WorkIt, oldest first, as {url, company, title, logo_url, company_domain}
        (the logo sources the website draws each job with); or {error}."""
        try:
            rows = self._applications("queued")
        except workit.WorkItError as error:
            return {"error": f"WorkIt Auto Apply couldn't read your queue ({error}). Paste a link instead."}
        queued = [_job(row["job"]) for row in reversed(rows) if row.get("open")]
        self._queued |= {job["url"]: {key: job[key] for key in QUEUED_JOB} for job in queued}
        return queued

    def applied(self) -> list[dict] | dict:
        """What the student applied to, on WorkIt (their Tracker's Applied, from any run or by hand), newest first,
        each as queue() names a job, with its `applied_at`; or {error}. The student page's Applied lists these
        after this run's."""
        try:
            rows = self._applications("applied")
        except workit.WorkItError as error:
            return {"error": f"WorkIt Auto Apply couldn't read what you applied to ({error})."}
        return [_job(row["job"]) | {"applied_at": row.get("applied_at")} for row in rows]

    def matches(self, filters: dict | None = None) -> list[dict] | dict:
        """Find jobs: the student's best matches that Auto Apply fills and they haven't queued or applied to, best
        first, under the Jobs page's own filters (MATCH_FILTERS); each as queue() names a job, with the facts its
        card shows (MATCH_FACTS), or {error}. Scoring takes WorkIt a while, so this waits up to MATCHES_WAIT."""
        query = [("size", MATCHES)] + [
            (key, value) for key, values in (filters or {}).items() if key in MATCH_FILTERS
            for value in (values if isinstance(values, list) else [values]) if value not in (None, "")]
        try:
            rows = self._client.call("GET", f"/applicants/{self._client.applicant_id()}/auto-apply/matches?"
                                     f"{urlencode(query)}", timeout=MATCHES_WAIT)
        except workit.WorkItError as error:
            if "experience bank is empty" in str(error):  # jobs.EmptyBank's 404
                return {"error": "Add your experience on WorkIt first, so we can find jobs that fit you."}
            return {"error": f"WorkIt Auto Apply couldn't find jobs for you ({error})."}
        jobs = [_job(row) | {key: row.get(key) for key in MATCH_FACTS} for row in rows]
        # A run started from these shows each job's logo, as one from the queue does.
        self._queued |= {job["url"]: {key: job[key] for key in QUEUED_JOB} for job in jobs}
        return jobs

    def _applications(self, stage: str) -> list[dict]:
        return self._client.call("GET", f"/applicants/{self._client.applicant_id()}/applications?stage={stage}")

    def usage(self) -> dict:
        """Today's model use: {used, cap, resets_at}, or {error}."""
        try:
            return self._client.call("GET", "/apply-app/usage")
        except workit.WorkItError as error:
            return {"error": str(error)}

    def status(self) -> dict:
        return {"running": self._running.is_set(), "said": self._said}

    def start(self, links: list | None = None) -> dict:
        """Start a run of `links` (Start), one at a time: {started} or {error}."""
        links = [str(link).strip() for link in links or [] if str(link).strip()]
        if self._start is None:
            return {"error": "This window can't start a run."}
        if not links:
            return {"error": "Tick a job in your queue, or paste a job posting's link."}
        if self._running.is_set():
            return {"error": "A run is going: its forms are in the window."}
        self._running.set()
        self._said = ""
        threading.Thread(target=self._run, args=(links,), daemon=True).start()
        return {"started": len(links)}

    def show_board(self, board: Dashboard) -> None:
        """The window shows `board`: a run's own Apply window, or the queue again. It draws each queued job's logo."""
        board.logos(self._queued)
        self._dashboard = board
        if self._window is not None:
            self._window.load_html(self._page())

    def _run(self, links: list[str]) -> None:
        try:
            self._start(links, self.show_board)
        except SetupError as error:  # no engine (W7), a Worker profile in use, no Chrome: one sentence
            self._said = str(error)
        except Exception as error:
            self._said = f"The run stopped: {type(error).__name__}: {error}"
        finally:
            self._running.clear()
            self.show_board(self._idle)

    # Settings (W5 step 5).

    def settings(self) -> dict:
        if self._window is not None:
            self._window.load_html(SETTINGS)
        return {}

    def settings_state(self) -> dict:
        return {"workers": first_run.workers(), "notices": NOTICES.is_file()}

    def set_workers(self, count: int) -> dict:
        return {"workers": first_run.set_workers(count)}

    def show_notices(self) -> dict:
        if not NOTICES.is_file():
            return {"error": "The third-party notices aren't in this copy of the app."}
        self._open_link(NOTICES.as_uri())
        return {}

    def back(self) -> dict:
        if self._window is not None:
            self._window.load_html(self._page())
        return {}

    def sign_out(self) -> dict:
        if self._running.is_set():
            return {"error": "A run is going: close its forms first."}
        try:
            self._client.sign_out()
        except workit.WorkItError as error:
            return {"error": f"WorkIt Auto Apply couldn't sign out ({error})."}
        if self._window is not None:
            self._window.load_html(SIGN_IN)
        return {}

    def remove_data(self) -> dict:
        """Remove All My Data (D25), then close the app: what it showed is gone."""
        if self._running.is_set():
            return {"error": "A run is going: close its forms first."}

        def forget() -> None:
            try:
                self._client.sign_out()
            except workit.WorkItError:
                pass  # its keychain item couldn't be removed: the data folder still goes

        said = self._remove(forget)
        if said.startswith("Removed") and self._window is not None:
            threading.Timer(2.0, self._window.destroy).start()
        return {"said": said}

    # Report a problem (D26): Settings' form, and an Application's card with its id.

    def review_report(self, category: str, note: str, contact_ok: bool = False, application_id: str = "",
                      include: bool = True) -> dict:
        """The report the form's answers make, kept for send_report: what it holds, a line each ({parts}); or
        {error}. With `application_id` it is about that Application, with its record and log when `include`."""
        self._report = None
        if not str(note).strip():
            return {"error": "Write what happened first."}
        row = self._application(str(application_id)) if application_id else None
        if application_id and row is None:
            return {"error": "WorkIt Auto Apply has nothing of that application on this computer."}
        try:
            self._report = report.build(str(category), str(note), PROFILE, row, bool(include), bool(contact_ok))
        except ValueError as error:  # a category the server doesn't take, or no profile file to mask the log with
            return {"error": f"The report can't go as it is: {error}."}
        return {"parts": report.parts(self._report)}

    def send_report(self, application_id: str = "") -> dict:
        """Send Report: the report review_report showed, as it was shown. {said}, or {error}. `application_id` is the
        Application the pressing form is about ("" for Settings'), so a report another form reviewed since doesn't go."""
        if self._report is None:
            return {"error": "Press Review Report first."}
        if str(self._report.get("application_id") or "") != str(application_id):
            return {"error": "Press Review Report again: another report was reviewed since."}
        try:
            report.send(self._report, self._client)
        except workit.CapReached:
            return {"error": "You've sent a lot of reports today. Send this one tomorrow."}
        except workit.WorkItError as error:
            return {"error": f"WorkIt didn't take the report ({error}). Try again."}
        self._report = None
        return {"said": "Sent. WorkIt keeps your report until its problem is fixed, then deletes it."}

    def _application(self, application_id: str) -> Row | None:
        """The Application a report is about: its Tracker row; else, for a form this run held (a rehearsal keeps no
        row for it), its tile with its newest Record."""
        from apply.student import RECORDS  # here: apply.student imports this module

        try:
            if row := FileTracker().get(application_id):
                return row
        except Exception:  # a Tracker that won't read: the run's tile may still name it
            pass
        state = self._dashboard.state()
        seen = next((c for c in state["tiles"] + state["items"] if c.get("application_id") == application_id), None)
        if seen is None:
            return None
        records = sorted((path for path in RECORDS.glob("*/*") if path.name.endswith(f"-{application_id}")),
                         key=lambda path: path.parent.name)
        try:
            status = Status(str(seen.get("status")))
        except ValueError:  # a rehearsal's "ready": held for the student to send
            status = Status.HELD
        return Row(application_id, str(seen.get("company") or ""), str(seen.get("role") or ""),
                   str(seen.get("posting_url") or ""), str(seen.get("job_system") or ""), status,
                   record=str(records[-1]) if records else "")

    def _page(self) -> str:
        """The app's window, which can start a run, shows the student page; one that can't keeps the developer
        page."""
        return student_page(self._dashboard) if self._start is not None else page(self._dashboard)

    def _html(self) -> str:
        """What the window shows now: SIGN_IN signed out, FIRST_RUN while a step is left, else the Apply window."""
        if not self.signed_in():
            return SIGN_IN
        return self._page() if self._first.step() == READY else FIRST_RUN


# Find jobs (Bridge.matches): how many to show, the Jobs page's filters it passes on, and what each card shows.
MATCHES = 30
MATCHES_WAIT = 90
MATCH_FILTERS = frozenset({"q", "location", "work_style", "role", "experience", "job_type", "posted_within",
                           "start_term", "visa"})
MATCH_FACTS = ("id", "location", "location_label", "work_style", "job_type", "experience_level", "salary_min",
               "salary_max", "salary_period", "start_term", "posted_at", "match", "highlights")


def _job(job: dict) -> dict:
    """A WorkIt job as the window names it (QUEUED_JOB), by the link Apply opens: its employer's form when the
    posting named one, else its job board's page."""
    return {"url": job.get("form_url") or job["apply_url"]} \
        | {key: job.get(key) or ("" if key in ("company", "title") else None) for key in QUEUED_JOB}


def notify(title: str, message: str) -> None:
    """macOS's own notice (Dashboard's `notify`). Only an app bundle may post one, so a Developer checkout's Python
    posts none; W8's bundle does."""
    if sys.platform != "darwin":
        return
    import Foundation

    center = Foundation.NSUserNotificationCenter.defaultUserNotificationCenter()
    if center is None:
        return
    notice = Foundation.NSUserNotification.alloc().init()
    notice.setTitle_(title)
    notice.setInformativeText_(message)
    center.deliverNotification_(notice)


def bring_forward() -> bool:
    """The app's window in front of every other app's, for Dashboard's `back` after a captcha done in a Worker's own
    window (KAN-855). On a Mac only, for now."""
    if sys.platform != "darwin":
        return False
    import AppKit  # pyobjc, which pywebview brings on a Mac
    from PyObjCTools import AppHelper

    AppHelper.callAfter(AppKit.NSApplication.sharedApplication().activateIgnoringOtherApps_, True)
    return True


def run(dashboard: Dashboard, client: workit.WorkIt | None = None,
        start: Callable[[list[str], Callable[[Dashboard], None]], None] | None = None) -> None:
    """The window, till the student closes it: SIGN_IN, then FIRST_RUN, then the Apply window (Bridge._html)."""
    import webview  # here, not at the top: the bridge and its tests need no window

    bridge = Bridge(dashboard, client, start=start)
    window = webview.create_window(TITLE, html=bridge._html(), js_api=bridge, width=1280, height=820,
                                   min_size=(900, 600))
    bridge._window = window
    closing(window)
    sign_in_link.listen()  # the built app takes WorkIt's sign-in link from macOS itself (W8)
    updates.start()  # the built app's Sparkle updater (W8 step 3)
    webview.start()  # no http_server: the page is a string, so pywebview opens no port either


def closing(window) -> None:
    """`kill <pid>` closes the window, so webview.start returns and each `finally` stops what it started. The CLI's own
    SIGTERM raises KeyboardInterrupt, which lands inside a Cocoa callback here: PyObjC turns it into an Objective-C
    exception and macOS aborts the app ("python quit unexpectedly"). A Python handler only runs once the main thread
    runs Python, and Cocoa's run loop may not for a long while, so the signal wakes a thread of its own instead."""
    if threading.current_thread() is not threading.main_thread():
        return
    read, write = os.pipe()
    os.set_blocking(write, False)
    signal.signal(signal.SIGTERM, lambda signum, frame: None)  # no KeyboardInterrupt: the thread below closes
    signal.set_wakeup_fd(write)

    def close() -> None:
        while os.read(read, 1) != bytes([signal.SIGTERM]):
            pass
        window.destroy()

    threading.Thread(target=close, daemon=True, name="close-on-kill").start()
