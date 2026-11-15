"""WorkIt Auto Apply's window (KAN-723, W5 of docs/desktop_application_auto_apply.md; D11, D12): one native window
(pywebview: WKWebView on a Mac) and no port.

The window shows the Apply window's own page (apply.dashboard's), served by no server: Dashboard(serve=False)
listens on nothing, and SHIM, put in the page before its scripts, sends the page's requests to `Bridge`, pywebview's
JavaScript bridge (js_api), which answers each one in this process through the same routes, checks and token as
the server (Dashboard.respond). The tiles' frames come from Bridge.frames as the server's /frames stream would; a
link to a file a tile lists opens in the system's own app.

Signed out, the window first shows SIGN_IN: Sign In with WorkIt opens WorkIt's /app-sign-in page in the default
browser with this sign-in's PKCE challenge (workit.pkce). The built app takes the code back from the page's
workit-auto-apply:// link (W8); a Developer checkout pastes it in the box, which only WorkIt's admins' page shows.
Then Bridge.trade signs in (WorkIt.trade). Next comes FIRST_RUN while any first-run step is left (apply.first_run:
Chrome, the disclosure and license, Screen Recording, the seed), then the Apply window.

A run (W5 step 4): with no run going, the Apply window has PANEL on top: the student's Auto Apply queue on WorkIt, a
box to paste one posting's link, Start, and today's model use against the Usage cap (USAGE, on every page of the
app). Start hands the links to `start` (apply.student.Runs), which rehearses them in the Workers and shows the run's
own Apply window, its tiles, till every form it held is closed; then the window shows the queue again. A run that
can't start (no engine, W7; a Worker profile in use) says why in one line.

The app's page loads no web font: Google Fonts would be a request the privacy page doesn't name (FONTS).

pywebview gives the page every public method of Bridge, and nothing whose name starts with "_".
"""

import base64
import re
import sys
import threading
import time
import webbrowser
from collections.abc import Callable

from apply import workit
from apply.adapters import SetupError
from apply.dashboard import FRAME_GAP, Dashboard
from apply.dashboard_page import STYLE
from apply.first_run import CHROME_DOWNLOAD, EULA, READY, FirstRun

TITLE = "WorkIt Auto Apply"
# How long Bridge.frames waits for a new frame before it answers none, so the page asks again.
FRAMES_WAIT = 1.0
# The Apply window's web font links, left out of the app's page: the system's fonts stand in.
FONTS = re.compile(r'<link[^>]+fonts\.googleapis\.com[^>]*>')
READY_JS = """const ready = new Promise(done => (window.pywebview && window.pywebview.api) ? done()
                                   : addEventListener('pywebviewready', () => done(), {once: true}));"""

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
<meta name="color-scheme" content="light dark"><style>{style}
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
document.getElementById('start').addEventListener('click', async () => {
  await ready;
  await window.pywebview.api.sign_in();
  form.hidden = false;
  said.textContent = 'Sign in on the WorkIt page that opened in your browser.';
});
form.addEventListener('submit', async event => {
  event.preventDefault();
  said.textContent = 'Signing in…';
  const got = await window.pywebview.api.trade(document.getElementById('pasted').value);
  if (got.error) said.textContent = got.error;
});
</script>""".replace("{style}", STYLE).replace("{ready}", READY_JS)

FIRST_RUN = """<!doctype html><meta charset="utf-8"><title>WorkIt Auto Apply</title>
<meta name="color-scheme" content="light dark"><style>{style}
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
<ul>
<li><b>To WorkIt:</b> what each AI call needs, without your private details such as your contact details, street
address and self-identification answers; your applications' stages; the answers you approve; your Auto Apply queue.
One application's record and log go only when you press Send Report.</li>
<li><b>To Groq and Google (Gemini):</b> the same AI prompts, sent by WorkIt with WorkIt's own key. Google's free
tier may use the prompts and answers it gets to improve its products, and people at Google may read them.</li>
<li><b>To job sites:</b> your answers, typed into each form as you would type them.</li>
</ul>
<p>The records of each application, the Chrome windows' profiles and sign-ins, and your job-site passwords (in the
Keychain) stay on your Mac. WorkIt Auto Apply never presses Submit: you do.</p>
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
</script>""".replace("{style}", STYLE).replace("{ready}", READY_JS)


# Today's model use against the Usage cap (W1, D6), on every page of the app, read again each minute.
USAGE = """<div id="usage" role="status" style="position: fixed; top: 0.4rem; right: 0.8rem; font-size: 0.8rem;
  opacity: 0.75; z-index: 20"></div>
<script>(async () => {
  {ready}
  await ready;
  const shown = document.getElementById('usage');
  const read = async () => { const use = await window.pywebview.api.usage();
    shown.textContent = use.error ? '' : `Model use today: ${use.used.toLocaleString()} of ${use.cap.toLocaleString()} tokens`; };
  read(); setInterval(read, 60000);
})();</script>""".replace("{ready}", READY_JS)

# With no run going: the queue, a pasted link, Start (Bridge.queue, Bridge.start).
PANEL = """<section id="run" style="max-width: 46rem; margin: 2.6rem auto 1rem; display: flex; flex-direction: column;
  gap: 0.6rem">
<h2>Your Auto Apply Queue</h2>
<p id="queue-said">Reading your queue on WorkIt…</p>
<ul id="queue" style="list-style: none; padding: 0; margin: 0"></ul>
<label>Or paste a job posting's link <input id="pasted" autocomplete="off" spellcheck="false" style="width: 100%"></label>
<div><button class="primary" id="start">Start</button></div>
<p id="run-said" role="alert"></p>
</section>
<script>(async () => {
  {ready}
  await ready;
  const api = window.pywebview.api, list = document.getElementById('queue'), said = document.getElementById('queue-said');
  const queued = await api.queue();
  if (queued.error) said.textContent = queued.error;
  else {
    said.textContent = queued.length ? 'WorkIt Auto Apply fills the jobs you tick, then holds each form for you to check and send.'
                                     : 'Your queue is empty: add jobs on WorkIt, or paste a link below.';
    for (const job of queued) {
      const row = document.createElement('li'), box = document.createElement('input'), name = document.createElement('label');
      box.type = 'checkbox'; box.checked = true; box.value = job.url; box.id = 'job-' + list.children.length;
      name.htmlFor = box.id; name.textContent = ` ${job.company}: ${job.title}`;
      row.append(box, name); list.append(row);
    }
  }
  const status = await api.status();
  if (status.said) document.getElementById('run-said').textContent = status.said;
  document.getElementById('start').addEventListener('click', async () => {
    const links = [...list.querySelectorAll('input:checked')].map(box => box.value);
    const pasted = document.getElementById('pasted').value.trim();
    if (pasted) links.push(pasted);
    const got = await api.start(links);
    document.getElementById('run-said').textContent = got.error || 'Starting the Workers…';
  });
})();</script>""".replace("{ready}", READY_JS)


def page(dashboard: Dashboard, panel: bool = False, usage: bool = False) -> str:
    """The Apply window's page with SHIM before its scripts and no web font; with PANEL on top (no run going), and
    USAGE."""
    html = FONTS.sub("", dashboard.page())
    extra = (PANEL if panel else "") + (USAGE if usage else "")
    if extra:
        html = html.replace("</style>", "</style>" + extra, 1)
    head = '<meta charset="utf-8">'
    return html.replace(head, head + SHIM, 1) if head in html else SHIM + html


class Bridge:
    """What the window's page may call (pywebview's js_api): the Apply window's routes, its frames and files, and
    the sign-in. `open_link` opens a URL in the default browser, or a file in the system's own app."""

    def __init__(self, dashboard: Dashboard, client: workit.WorkIt | None = None,
                 open_link: Callable[[str], object] = webbrowser.open, first_run: FirstRun | None = None,
                 start: Callable[[list[str], Callable[[Dashboard], None]], None] | None = None):
        """`start(links, show)`, when given, runs `links` and calls `show(board)` with the run's own Apply window
        (apply.student.Runs.run); the app's pages then have PANEL and USAGE."""
        self._dashboard = self._idle = dashboard
        self._client = client or workit.WorkIt()
        self._open_link = open_link
        self._first = first_run or FirstRun()
        self._start = start
        self._running = threading.Event()  # a run is going
        self._said = ""  # why the last run couldn't start or stopped
        self._verifier: str | None = None  # this sign-in's PKCE verifier, till its code is traded
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
        """The student's queued, open jobs on WorkIt, oldest first, as {url, company, title}; or {error}."""
        try:
            rows = self._client.call("GET", f"/applicants/{self._client.applicant_id()}/applications?stage=queued")
        except workit.WorkItError as error:
            return {"error": f"WorkIt Auto Apply couldn't read your queue ({error}). Paste a link instead."}
        jobs = [row["job"] for row in reversed(rows) if row.get("open")]
        return [{"url": job.get("form_url") or job["apply_url"], "company": job.get("company") or "",
                 "title": job.get("title") or ""} for job in jobs]

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
        """The window shows `board`: a run's own Apply window, or the queue again."""
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

    def _page(self) -> str:
        board = self._dashboard
        return page(board, panel=board is self._idle and self._start is not None, usage=self._start is not None)

    def _html(self) -> str:
        """What the window shows now: SIGN_IN signed out, FIRST_RUN while a step is left, else the Apply window."""
        if not self.signed_in():
            return SIGN_IN
        return self._page() if self._first.step() == READY else FIRST_RUN


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
    webview.start()  # no http_server: the page is a string, so pywebview opens no port either
