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
Then Bridge.trade signs in (WorkIt.trade) and the window shows the Apply window.

pywebview gives the page every public method of Bridge, and nothing whose name starts with "_".
"""

import base64
import time
import webbrowser
from collections.abc import Callable

from apply import workit
from apply.dashboard import FRAME_GAP, Dashboard
from apply.dashboard_page import STYLE

TITLE = "WorkIt Auto Apply"
# How long Bridge.frames waits for a new frame before it answers none, so the page asks again.
FRAMES_WAIT = 1.0

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
const ready = new Promise(done => (window.pywebview && window.pywebview.api) ? done()
                                   : addEventListener('pywebviewready', () => done(), {once: true}));
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
</script>""".replace("{style}", STYLE)


def page(dashboard: Dashboard) -> str:
    """The Apply window's page with SHIM before its scripts."""
    html = dashboard.page()
    head = '<meta charset="utf-8">'
    return html.replace(head, head + SHIM, 1) if head in html else SHIM + html


class Bridge:
    """What the window's page may call (pywebview's js_api): the Apply window's routes, its frames and files, and
    the sign-in. `open_link` opens a URL in the default browser, or a file in the system's own app."""

    def __init__(self, dashboard: Dashboard, client: workit.WorkIt | None = None,
                 open_link: Callable[[str], object] = webbrowser.open):
        self._dashboard = dashboard
        self._client = client or workit.WorkIt()
        self._open_link = open_link
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
            self._window.load_html(page(self._dashboard))
        return {"email": account.email}


def run(dashboard: Dashboard, client: workit.WorkIt | None = None) -> None:
    """The window, till the student closes it: SIGN_IN while signed out, else the Apply window."""
    import webview  # here, not at the top: the bridge and its tests need no window

    bridge = Bridge(dashboard, client)
    window = webview.create_window(TITLE, html=page(dashboard) if bridge.signed_in() else SIGN_IN, js_api=bridge,
                                   width=1280, height=820, min_size=(900, 600))
    bridge._window = window
    webview.start()  # no http_server: the page is a string, so pywebview opens no port either
