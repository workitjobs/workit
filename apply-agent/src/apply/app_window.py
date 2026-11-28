"""WorkIt Auto Apply's window (KAN-723, W5 of docs/desktop_application_auto_apply.md; D11, D12): one native window
(pywebview: WKWebView on a Mac) and no port.

The app's window shows the student page (KAN-867: window/, built into STUDENT_PAGE); a window that can start no run
shows the Apply window's own page (apply.dashboard's). `apply app` gives its window a start in a Developer checkout too
(apply.student.app), so `apply app --max-plan` shows the student page. Either is served by no server:
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
(Bridge.matches, KAN-882; during a run its picks join the run, as links sent in do), and a step away the student's Auto Apply queue on WorkIt (Bridge.queue), a box to paste
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

Links sent in (`uv run apply app <link>...`): an agent or a script hands the running window links with no
port and no clicks. `send_links` writes them as one file in INBOX; the window takes them each INBOX_EVERY
(Bridge._take_inbox) once it is signed in and set up. With no run going they start one, as Start does; while one
goes, each is filled beside its forms (Dashboard.into), else it waits for the next run. Either way, Apply submits a
form only once the student approves it (ADR 0006).

pywebview gives the page every public method of Bridge, and nothing whose name starts with "_".
"""

import atexit
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
from urllib.parse import urlencode, urlsplit

import psutil

from apply import (
    build,
    first_run,
    queued_names,
    report,
    safety,
    sign_in_link,
    updates,
    workit,
)
from apply.adapters import SetupError
from apply.answers_tab import Refused
from apply.dashboard import FRAME_GAP, QUEUED_JOB, Dashboard
from apply.dashboard_page import STYLE
from apply.first_run import CHROME_DOWNLOAD, EULA, NOTICES, READY, FirstRun
from apply.home import HOME
from apply.model import Status, job_title
from apply.tracker import FileTracker, Row

TITLE = "WorkIt Auto Apply"
# The student page, built from window/ by Vite (`npm run build`) into one file: CI checks it matches its source.
STUDENT_PAGE = Path(__file__).with_name("student_page") / "index.html"
# WorkIt's logo, the built app's icon (scripts/build_app.py's ICON): a checkout's window shows it in the Dock too.
ICON = Path(__file__).parents[2] / "assets" / "app-icon.png"
# The Applicant profile's file, whose values a report's log is masked with (apply.report.build): never its folder.
PROFILE = HOME / "applicant-profile.yaml"
# How long Bridge.frames waits for a new frame before it answers none, so the page asks again.
FRAMES_WAIT = 1.0
# The Apply window's web font links, left out of the app's page: the system's fonts stand in.
FONTS = re.compile(r'<link[^>]+fonts\.googleapis\.com[^>]*>')
# Links sent to the window (send_links), one JSON file each, and how often the window looks; the window's PID note.
INBOX = HOME / "app-inbox"
INBOX_EVERY = 2.0
CLOSE_GUARD_EVERY = 1.0  # how often the quit question's count of held forms is read again (guard_close)
PID_NOTE = HOME / "app.pid"
LINK = re.compile(r"^https?://\S+$")
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
<section id="safety" hidden>
<h1>How Careful Should Apply Be?</h1>
{levels}
<p>{always} You can change it any time in Settings.</p>
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
  show(await window.pywebview.api[button.dataset.do](...(button.dataset.level ? [button.dataset.level] : [])));
});
ready.then(async () => {
  show(await window.pywebview.api.first_run());
  setInterval(async () => show(await window.pywebview.api.first_run()), 1500);  // Chrome installed, the seed's steps
});
</script>""".replace("{style}", APP_STYLE).replace("{ready}", READY_JS).replace("{disclosure}", DISCLOSURE).replace(
    "{levels}", "".join(f'<div class="row"><button data-do="choose_safety" data-level="{level}">{html.escape(name)}'
                        f'</button></div><p>{html.escape(words)}</p>' for level, (name, words) in safety.SAID.items())
).replace("{always}", html.escape(safety.ALWAYS))

SETTINGS = """<!doctype html><meta charset="utf-8"><title>WorkIt Auto Apply</title>
<meta name="color-scheme" content="light"><style>{style}
  main.settings { max-width: 34rem; margin: 8vh auto; display: flex; flex-direction: column; gap: 0.8rem; }
  main.settings .row { display: flex; gap: 0.6rem; flex-wrap: wrap; }
  main.settings .top { justify-content: space-between; align-items: center; }
</style>
<main class="settings">
<div class="row top"><h1>Settings</h1><button data-do="back">Back</button></div>
<label>Workers at once <select id="workers"><option value="0" id="workers-auto">Automatic</option>
<option>1</option><option>2</option><option>3</option><option>4</option></select></label>
<p>Each Worker is a full Chrome, about 0.5 to 1 GB of memory. Automatic picks the count from this Mac's memory.
The next Start uses the new count.</p>
<label>How careful should Apply be? <select id="safety">{levels}</select></label>
<p id="safety-said">{careful}</p>
<p>{always} A policy you set yourself in policies.yaml wins over the level. The next Start uses the new level.</p>
<div class="row"><button id="show-disclosure">What Leaves Your Mac</button>
<button data-do="show_license">Read the License</button>
<button data-do="show_notices" id="notices" hidden>Third-Party Notices</button></div>
<div id="disclosure" hidden>{disclosure}</div>
<section id="claude" hidden><h2>Claude (Developer)</h2>
<label><input type="checkbox" id="best"> Write essays, cover letters and the final check with Opus 5.5</label>
<p>Off, they run on Sonnet: slower to use up your plan, a little weaker.</p>
<p id="claude-dropped" role="status"></p>
<p id="claude-login"></p>
<p>To use another subscription, run <code>claude setup-token</code>, then <code>uv run apply claude-token</code>
and paste the token. <code>uv run apply claude-token --forget</code> goes back to your claude login.</p>
</section>
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
const careful = document.getElementById('safety'), levels = {said};
const sayLevel = () => { document.getElementById('safety-said').textContent = levels[careful.value]; };
careful.addEventListener('change', async () => {
  sayLevel(); await ready; await window.pywebview.api.set_safety_level(careful.value); });
const best = document.getElementById('best');
best.addEventListener('change', async () => { await ready; await window.pywebview.api.set_best_model(best.checked); });
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
  document.getElementById('workers-auto').textContent = `Automatic (${state.automatic} for this Mac)`;
  count.value = String(state.workers || 0);
  careful.value = state.safety; sayLevel();
  document.getElementById('notices').hidden = !state.notices;
  if (state.claude) {
    document.getElementById('claude').hidden = false;
    best.checked = state.claude.best;
    document.getElementById('claude-login').textContent = `Claude signs in with ${state.claude.login}.`;
    document.getElementById('claude-dropped').textContent = state.claude.dropped || '';
  }
});
</script>""".replace("{style}", APP_STYLE).replace("{ready}", READY_JS).replace("{disclosure}", DISCLOSURE).replace(
    "{categories}", "".join(f'<option value="{key}">{html.escape(words)}</option>' for key, words in report.CATEGORIES.items())
).replace("{levels}", "".join(f'<option value="{level}">{html.escape(name)}</option>' for level, (name, _) in safety.SAID.items())
          ).replace("{careful}", html.escape(safety.SAID[safety.DEFAULT][1])).replace("{always}", html.escape(safety.ALWAYS)
          ).replace("{said}", json.dumps({level: words for level, (_, words) in safety.SAID.items()}))


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
                 forward: Callable[[], object] = lambda: bring_forward(), name: Callable[[str], dict] | None = None):
        """`start(links, show)`, when given, runs `links` and calls `show(board)` with the run's own Apply window
        (apply.student.Runs.run); the window then shows the student page. `name(link)` names a link that waits to
        start and no queue named (default apply.queued_names's, with plain reads)."""
        self._dashboard = self._idle = dashboard
        self._client = client or workit.WorkIt()
        self._open_link = open_link
        self._first = first_run or FirstRun()
        self._start = start
        self._remove = remove
        self._link = link  # the sign-in page's link, handed to this window (apply.sign_in_link: ready, clear, take)
        self._forward = forward  # the window brought in front of the browser
        self._name = name or queued_names.namer(self._client)
        self._running = threading.Event()  # a run is going
        self._said = ""  # why the last run couldn't start or stopped
        self._queued: dict[str, dict] = {}  # each queued job (QUEUED_JOB) by its link, for a run's window (KAN-871)
        self._renamed: dict[str, dict] = {}  # what `name` gave each applied job whose title is a page's chrome
        self._verifier: str | None = None  # this sign-in's PKCE verifier, till its code is traded
        self._report: dict | None = None  # the report the window showed, till Send Report sends it
        self._window = None  # the pywebview window, once run() made it
        self._waiting: list[str] = []  # links sent in (send_links) that wait for the next run
        self._todo_scanning = threading.Lock()  # held while a to-do scan reads mail: one at a time
        self._todo_scan: dict | None = None  # what the last to-do scan did (todo_scan.Scan.shown), and when

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

    def open_posting(self, url: str) -> bool:
        """A job's posting, in the student's own browser, for "Apply on the company's site": only a web link a tile or
        item of this run lists as its posting. Any other link opens nothing."""
        state = self._dashboard.state()
        listed = {str(s.get("posting_url") or "") for s in [*state.get("tiles", []), *state.get("items", [])]}
        if str(url) not in listed or urlsplit(str(url)).scheme not in ("http", "https"):
            return False
        self._open_link(str(url))
        return True

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

    def choose_safety(self, level: str) -> dict:
        if level in safety.LEVELS:
            self._first.choose_safety(level)
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
        return [self._named_again(_job(row["job"])) | {"applied_at": row.get("applied_at")} for row in rows]

    def _named_again(self, job: dict) -> dict:
        """A job whose WorkIt title is a page's chrome (model.job_title), as Apply wrote it before it checked:
        "Log in or create account | Amazon.jobs" for an Amazon posting behind a sign-in wall. It takes the title it
        was queued with, else the one its listing or job system names (`name`, read once a link), else none."""
        if job["title"] and not job_title(job["title"]):
            url = job["url"]
            if url not in self._queued and url not in self._renamed:
                self._renamed[url] = self._name(url)
            job["title"] = job_title((self._queued.get(url) or self._renamed.get(url) or {}).get("title") or "")
        return job

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
        """Start a run of `links` (Start), one at a time: {started} or {error}. While a run goes (Find jobs beside it,
        as a run of `apply app <link>` keeps going for hours), they join it as links sent in do (_join): {added}."""
        links = [str(link).strip() for link in links or [] if str(link).strip()]
        if self._start is None:
            return {"error": "This window can't start a run."}
        if not links:
            return {"error": "Tick a job in your queue, or paste a job posting's link."}
        if self._running.is_set():
            self._join(links)
            return {"added": len(links)}
        self._running.set()
        self._said = ""
        threading.Thread(target=self._run, args=(links,), daemon=True).start()
        return {"started": len(links)}

    def _take_inbox(self, inbox: Path = INBOX) -> None:
        """Links sent in (send_links): a run of them when none goes, once signed in and set up; while one goes,
        each into its Workers beside its forms (Dashboard.into), else it waits for the next run."""
        if self._start is None or not (self._waiting or any(inbox.glob("*.json"))):
            return
        if not self.signed_in() or self._first.step() != READY:
            return  # they stay in the inbox till the student is signed in and set up
        waiting = {workit.job_key(link) for link in self._waiting}
        links = [link for link in take_links(inbox) if workit.job_key(link) not in waiting]
        if self._running.is_set():
            self._join(links)
            return
        links, self._waiting = self._waiting + links, []
        if links and "error" in self.start(links):
            self._waiting = links

    def _join(self, links: list[str]) -> None:
        """`links` into the run going, each into its Workers beside its forms (Dashboard.into); one the run won't
        take waits for the next run."""
        for link in links:
            try:
                self._dashboard.into(link)
            except Refused:  # this run takes no new links (a CDP Worker), or it is ending
                self._waiting.append(link)

    def show_board(self, board: Dashboard) -> None:
        """The window shows `board`: a run's own Apply window, or the queue again. It draws each queued job's logo,
        and names each other link as it waits to start (a link sent in or pasted)."""
        board.logos(self._queued)
        board.names_by(self._name)
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
        """With `apply app --max-plan` in a Developer checkout, `claude` too: the Best model's switch, which login
        `claude -p` uses, and why the Best model last paused."""
        state = {"workers": first_run.chosen_workers() or 0, "automatic": first_run.automatic_workers(),
                 "notices": NOTICES.is_file(), "safety": first_run.safety_level() or safety.DEFAULT}
        from apply import student

        if not build.STUDENT and os.environ.get(student.MAX_PLAN):
            from apply import claude_cli

            state["claude"] = {"best": first_run.best_model(), "login": claude_cli.login(), "dropped": claude_cli.dropped}
        return state

    def set_best_model(self, on: bool) -> dict:
        return {"best": first_run.set_best_model(on)}

    def set_workers(self, count: int) -> dict:
        """0 is Settings' Automatic: the count from the computer's memory."""
        return {"workers": first_run.set_workers(int(count) or None)}

    def set_safety_level(self, level: str) -> dict:
        try:
            return {"safety": first_run.set_safety_level(level)}
        except ValueError as error:
            return {"error": str(error)}

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

    # Application to-dos (developer only, apply.todos): off, each refuses and the page shows no To-dos.

    def todos(self) -> dict:
        """Every to-do, open first, with the last scan and whether one is going; {enabled: false} when off."""
        if not todos_on():
            return {"enabled": False, "error": todos_off()}
        from apply.todos import TodoStore

        return {"enabled": True, "todos": [t.shown() for t in TodoStore().all()], "scan": self._todo_scan,
                "scanning": self._todo_scanning.locked()}

    def scan_todos(self, wait: bool = False) -> dict:
        """Scan mail for to-dos now, in a thread of its own unless `wait`. A scan already going is not started again:
        `wait` waits for it and gives its result."""
        if not todos_on():
            return {"enabled": False, "error": todos_off()}
        if not self._todo_scanning.acquire(blocking=False):
            if not wait:
                return {"scanning": True}
            with self._todo_scanning:  # a scan already going: wait for it, then show its result
                pass
            return self.todos()
        if wait:
            self._scan_todos(held=True)
            return self.todos()
        threading.Thread(target=self._scan_todos, kwargs={"held": True}, daemon=True, name="todo-scan").start()
        return {"scanning": True}

    def mark_todo(self, todo_id: str, status: str) -> dict:
        """A to-do marked done, dismissed, or open again."""
        if not todos_on():
            return {"enabled": False, "error": todos_off()}
        from apply.todos import TodoStore

        try:
            return {"todo": TodoStore().mark(str(todo_id), str(status)).shown()}
        except KeyError:
            return {"error": f"No such to-do: {todo_id}."}
        except ValueError as error:
            return {"error": str(error)}

    def _scan_todos(self, held: bool = False) -> None:
        """One scan, its result kept for the page; a failure is kept as its error, never raised."""
        if not held and not self._todo_scanning.acquire(blocking=False):
            return
        try:
            from apply import todo_scan

            try:
                done = todo_scan.live().shown()
            except Exception as error:
                done = {"errors": [f"{type(error).__name__}: {error}"]}
            self._todo_scan = {**done, "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
            print(f"To-do scan: read {done.get('read', 0)} mails, {done.get('added', 0)} new to-dos"
                  + (f"; {'; '.join(done['errors'])}" if done.get("errors") else ""), file=sys.stderr)
        finally:
            self._todo_scanning.release()

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


def badge(count: int) -> None:
    """The Dock icon's badge: how many forms wait on the student, none for 0 (Dashboard's `badge`). On a Mac only, and
    never an error where there is no Dock (a test, a Developer checkout without an app bundle)."""
    if sys.platform != "darwin":
        return
    try:
        import AppKit  # pyobjc, which pywebview brings on a Mac
        from PyObjCTools import AppHelper
    except ImportError:
        return
    label = str(count) if count > 0 else ""
    AppHelper.callAfter(lambda: AppKit.NSApplication.sharedApplication().dockTile().setBadgeLabel_(label))


def look_like_the_app(icon: Path = ICON) -> bool:
    """A Developer checkout's window as WorkIt Auto Apply in the Dock and the menu bar: its process is Python, so
    macOS showed Python's name and a blank page for its icon. The built app's bundle names it and gives its icon
    (scripts/build_app.py), and has no `icon` file beside its code, so this changes nothing there. On a Mac only, and
    before webview.start, so the menu bar reads the name as it starts. True when the icon was set."""
    if sys.platform != "darwin" or build.STUDENT or not icon.is_file():
        return False
    try:
        import AppKit  # pyobjc, which pywebview brings on a Mac
        import Foundation
    except ImportError:
        return False
    info = Foundation.NSBundle.mainBundle().infoDictionary()
    if info is not None:  # Python's own Info.plist, read once: the menu bar names the app from it
        info["CFBundleName"] = TITLE
    image = AppKit.NSImage.alloc().initWithContentsOfFile_(str(icon))
    if image is None:
        return False
    AppKit.NSApplication.sharedApplication().setApplicationIconImage_(image)
    return True


def bring_forward() -> bool:
    """The app's window in front of every other app's, for Dashboard's `back` after a captcha done in a Worker's own
    window (KAN-855). On a Mac only, for now."""
    if sys.platform != "darwin":
        return False
    import AppKit  # pyobjc, which pywebview brings on a Mac
    from PyObjCTools import AppHelper

    AppHelper.callAfter(AppKit.NSApplication.sharedApplication().activateIgnoringOtherApps_, True)
    return True


def links_given(arguments: list[str]) -> tuple[list[str], list[str]]:
    """The links in `apply app`'s arguments, and the words that aren't links. An argument may hold several links on
    lines of their own: zsh passes a variable's lines as one argument (`apply app $links`), which once sent the window
    a single unusable link, so a 28-job run never started."""
    words = [word for argument in arguments for word in argument.split()]
    return [w for w in words if LINK.match(w)], [w for w in words if not LINK.match(w)]


def send_links(links: list[str], inbox: Path = INBOX) -> Path:
    """Hand `links` to the running window (Bridge._take_inbox): one file in `inbox`, only the user's to read, written
    whole before it is named .json so the window never reads half of it."""
    inbox.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = inbox / f"{time.time_ns()}-{os.getpid()}.json"
    part = path.with_suffix(".part")
    part.write_text(json.dumps({"links": list(links)}), encoding="utf-8")
    part.chmod(0o600)
    part.rename(path)
    return path


def take_links(inbox: Path = INBOX) -> list[str]:
    """The links sent in since the last take, oldest first, one per posting (workit.job_key: a Greenhouse board's
    link and its embed's are one job); every file read is removed. A file that isn't a list of links is dropped."""
    links: list[str] = []
    for path in sorted(inbox.glob("*.json")):
        try:
            links += [str(link).strip() for link in json.loads(path.read_text(encoding="utf-8"))["links"]]
        except (OSError, ValueError, KeyError, TypeError):
            pass
        path.unlink(missing_ok=True)
    kept: dict[str, str] = {}
    for link in links:
        if LINK.match(link):
            kept.setdefault(workit.job_key(link), link)
    return list(kept.values())


def running(note: Path = PID_NOTE) -> int | None:
    """The PID of the WorkIt Auto Apply window running now (run() notes it), or None."""
    try:
        pid = int(note.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return pid if psutil.pid_exists(pid) else None


def _watch_inbox(bridge: Bridge) -> None:
    while True:
        try:
            bridge._take_inbox()
        except Exception as error:  # a bad take never ends the watch
            print(f"Couldn't take the links sent in: {type(error).__name__}: {error}", file=sys.stderr)
        time.sleep(INBOX_EVERY)


def todos_on() -> bool:
    """Whether the application to-do tracker is on (apply.todos.enabled), never importing it in the Student build."""
    if build.STUDENT:
        return False
    from apply import todos

    return todos.enabled()


def todos_off() -> str:
    """Why the to-do tracker refuses: the flag's off, or this is the Student build, which has none."""
    if build.STUDENT:
        return "The application to-do tracker isn't in this build."
    from apply import todos

    return todos.OFF


def _scan_todos_often(bridge: Bridge, sleep: Callable[[float], None] = time.sleep) -> None:
    """The to-do scan's schedule: now, then every todo_scan.EVERY seconds, till the window closes."""
    from apply import todo_scan

    while True:
        bridge._scan_todos()
        sleep(todo_scan.EVERY)


def run(dashboard: Dashboard, client: workit.WorkIt | None = None,
        start: Callable[[list[str], Callable[[Dashboard], None]], None] | None = None) -> None:
    """The window, till the student closes it: SIGN_IN, then FIRST_RUN, then the Apply window (Bridge._html)."""
    import webview  # here, not at the top: the bridge and its tests need no window

    steady_windows()
    bridge = Bridge(dashboard, client, start=start)
    window = webview.create_window(TITLE, html=bridge._html(), js_api=bridge, width=1280, height=820,
                                   min_size=(900, 600))
    bridge._window = window
    late_replies(window)
    closing(window)
    window.events.closing += lambda: guard_close(window, bridge)
    threading.Thread(target=_guard_closes, args=(window, bridge), daemon=True, name="close-guard").start()
    sign_in_link.listen()  # the built app takes WorkIt's sign-in link from macOS itself (W8)
    PID_NOTE.parent.mkdir(parents=True, exist_ok=True)
    PID_NOTE.write_text(str(os.getpid()), encoding="utf-8")
    threading.Thread(target=_watch_inbox, args=(bridge,), daemon=True, name="inbox").start()
    if todos_on():  # the application to-do tracker scans mail on open and every todo_scan.EVERY seconds
        threading.Thread(target=_scan_todos_often, args=(bridge,), daemon=True, name="todo-schedule").start()
    if not build.STUDENT:  # a terminal's agent reads and drives a Developer checkout's window (`apply window`)
        from apply import app_control

        threading.Thread(target=app_control.watch, args=(bridge,), daemon=True, name="control").start()
    updates.start()  # the built app's Sparkle updater (W8 step 3)
    look_like_the_app()
    try:
        webview.start()  # no http_server: the page is a string, so pywebview opens no port either
    finally:
        PID_NOTE.unlink(missing_ok=True)


class SteadyWindows(dict):
    """pywebview's windows by uid, whose views are snapshots: a window that closes while one is read leaves it whole.
    On a Mac, a quit (Cmd-Q, the Dock's Quit) reads every window's close question in turn, and with held forms that
    question is a dialog whose run loop runs our `closing` thread's `window.destroy`: the window's close took it out
    of the dict mid-read, and the app died with `<class 'RuntimeError'>: dictionary changed size during iteration`
    (run7, 2026-11-26)."""

    def __iter__(self):
        return iter(list(super().keys()))

    def keys(self):
        return list(super().keys())

    def values(self):
        return list(super().values())

    def items(self):
        return list(super().items())


def steady_windows(system: str = sys.platform, view=None) -> None:
    """On a Mac, make pywebview's Cocoa window list (BrowserView.instances) a SteadyWindows. Its other backends
    read no window list while a window closes. `view` is the class that holds the list (tests)."""
    if view is None:
        if system != "darwin":
            return
        from webview.platforms.cocoa import BrowserView as view
    if not isinstance(view.instances, SteadyWindows):
        view.instances = SteadyWindows(view.instances)


def line_by_line(*streams) -> None:
    """Each line goes out as it is written: under nohup, stdout and stderr are files, so Python held the run's lines
    in a block buffer, and its log could not be followed live (nor read whole after a crash). A stream that can't
    change (a test's capture) stays as it is."""
    for stream in streams or (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(line_buffering=True)
        except (AttributeError, ValueError, OSError):
            pass


REPLY = 'window.pywebview._returnValuesCallbacks["'  # how pywebview hands a js_api method's return to the page


def late_replies(window) -> None:
    """A js_api method's return that comes back after its page was replaced (load_html: Go on, Back, the board) finds
    no callback there: pywebview's reply thread raised JavascriptException ("... is not a function") and logged a
    traceback with the whole reply, a long `matches` wait's 30 jobs in it. No page waits on it, so it is dropped. Any
    other script's error still raises."""
    evaluate = window.evaluate_js

    def replying(script, *args, **kwargs):
        try:
            return evaluate(script, *args, **kwargs)
        except Exception as error:
            gone = type(error).__name__ == "JavascriptException" and "TypeError" in str(error)
            if isinstance(script, str) and script.startswith(REPLY) and gone:
                return None
            raise
    window.evaluate_js = replying


def close_words(held: int) -> str:
    """The question before the app quits with `held` forms open and waiting for the student: quitting closes them."""
    forms = "Your filled form" if held == 1 else f"Your {held} filled forms"
    return f"Quit WorkIt Auto Apply? {forms} waiting for you will close. Nothing gets submitted."


def guard_close(window, bridge: Bridge) -> None:
    """Ask before the window closes (or the app quits) only while a form is held for the student, naming how many
    (close_words): pywebview's `confirm_close` and its question's words, read when the window is asked to close. The
    `closing` event runs this just before `confirm_close` is read; the words are read before it on a Mac, so
    _guard_closes keeps them fresh too."""
    held = bridge._dashboard.held()
    words = getattr(window, "localization", None)  # pywebview makes it once the window starts
    if held and words is not None:
        words["global.quitConfirmation"] = close_words(held)
    window.confirm_close = held > 0


def _guard_closes(window, bridge: Bridge) -> None:
    said = ""
    while True:
        try:
            guard_close(window, bridge)
            said = ""
        except Exception as error:  # a bad read never ends the guard, and says so once, not every second
            if (line := f"Couldn't count the held forms: {type(error).__name__}: {error}") != said:
                print(line, file=sys.stderr)
            said = line
        time.sleep(CLOSE_GUARD_EVERY)


# The signals that quit the app as its window's close does. Ctrl-C in its terminal (SIGINT) aborted it inside Cocoa as
# SIGTERM did, and a closed terminal (SIGHUP) ended it at once: neither ran a `finally`, so its Workers' Chromes stayed.
QUITS = tuple(getattr(signal, name) for name in ("SIGTERM", "SIGINT", "SIGHUP") if hasattr(signal, name))


def closing(window) -> None:
    """`kill <pid>`, Ctrl-C or a closed terminal (QUITS) closes the window, so webview.start returns and each `finally` stops what it started. The CLI's own
    SIGTERM raises KeyboardInterrupt, which lands inside a Cocoa callback here: PyObjC turns it into an Objective-C
    exception and macOS aborts the app ("python quit unexpectedly"). A Python handler only runs once the main thread
    runs Python, and Cocoa's run loop may not for a long while, so the signal wakes a thread of its own instead. A
    second QUITS while it closes ends the app at once."""
    if threading.current_thread() is not threading.main_thread():
        return
    read, write = os.pipe()
    os.set_blocking(write, False)
    for number in QUITS:  # no KeyboardInterrupt: the thread below closes
        signal.signal(number, lambda signum, frame: None)
    signal.set_wakeup_fd(write)

    def close() -> None:
        while os.read(read, 1)[0] not in QUITS:
            pass
        window.destroy()
        # A second one while it closes (a stuck window, a slow stop): end now, the Chromes stopped first (atexit).
        while (number := os.read(read, 1)[0]) not in QUITS:
            pass
        atexit._run_exitfuncs()
        os._exit(128 + number)

    threading.Thread(target=close, daemon=True, name="close-on-kill").start()
