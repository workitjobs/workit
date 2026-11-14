"""Page code and the Fill engine through the worker extension's chrome.debugger (KAN-839, the W6
spike). A Chrome Web Store copy of the extension may run code that isn't in its package only
through the Debugger API or the User Scripts API, and User Scripts is for the user's own code; so
these ops (`cdp.eval`, `cdp.load`, `cdp.keep`, `cdp.script`) run Apply's page code and the engine
through the debugger. Measured here on Chrome for Testing, with user scripts off as in CI:

- page code reaches each frame's MAIN world (the top, a same-site frame, a frame from another site
  in its own process) where the page's CSP forbids eval, which the `eval` op can't;
- Runtime is never turned on: a page that watches for it (a getter DevTools would read off a
  console call's argument) sees nothing;
- the engine, held in the extension's memory, loads in every frame, and one whose sha256 differs is
  refused;
- an early script runs before the page's own code in every frame of the tab, but not in a pop-up
  the page opens: a new tab, outside the tab's debugger session. So the guards stay registered
  content scripts, which Chrome puts in every tab;
- a saved form fills the same through the debugger as through user scripts.

Skips without Chrome for Testing; CI installs it."""

import http.server
import json
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from apply import fill_engine
from apply.plain import demo, script
from apply.plain.bridge import Bridge, PortError
from apply.plain.launcher import PlainWorkers, chrome_for_testing
from apply.plain.page import PortPage
from apply.plain.script import wrap

try:
    chrome_for_testing()
    HAVE_CHROME = True
except FileNotFoundError:
    HAVE_CHROME = False

pytestmark = pytest.mark.skipif(not HAVE_CHROME, reason="needs Chrome for Testing (uv run playwright install chromium)")

NONCE = "n0nce"
CSP = f"script-src 'nonce-{NONCE}'; object-src 'none'"
# A page that notices Runtime turned on: DevTools reads a console call's arguments, which runs the getter.
WATCH = """window.__runtimeSeen = false;
const probe = new Error('probe');
Object.defineProperty(probe, 'stack', {configurable: true, get() { window.__runtimeSeen = true; return ''; }});
setInterval(() => console.debug(probe), 50);"""


def _page(name: str, body: str = "") -> bytes:
    return (f"<!doctype html><title>{name}</title><script nonce='{NONCE}'>window.__mark = {json.dumps(name)};"
            f"window.__earlyFirst = window.__applyEarly === true; {WATCH}</script><h1>{name}</h1>{body}").encode()


class Site:
    """`/top` with a same-site frame and one from another site (localhost, its own process), every
    page under a CSP that forbids eval."""

    def __init__(self):
        site = self

        class Pages(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                url = urlparse(self.path)
                if url.path == "/top":
                    body = _page("top", f"<iframe src='/frame?name=same'></iframe>"
                                        f"<iframe src='http://localhost:{site.port}/frame?name=away'></iframe>")
                else:
                    body = _page(parse_qs(url.query).get("name", ["frame"])[0])
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Security-Policy", CSP)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_):
                pass

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Pages)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.port}"


@pytest.fixture(scope="module")
def site():
    site = Site()
    yield site
    site.server.shutdown()


@pytest.fixture(scope="module")
def worker():
    """One plain Worker (Chrome for Testing, user scripts off) for the module, stopped after."""
    folder = Path(tempfile.mkdtemp(prefix="apw-cdp-", dir="/tmp"))
    workers = PlainWorkers(folder, kind="testing", bridge=Bridge(folder / "w.sock"))
    try:
        yield workers.launch(0).connection
    finally:
        workers.stop_all()


@pytest.fixture
def page(worker, site):
    """A new background tab on /top, with the other tabs closed."""
    old = [t["tab"] for t in worker.call("tabs.query")]
    page = PortPage(worker, worker.call("tabs.create", url="about:blank", active=False)["tab"])
    for tab in old:
        worker.call("tabs.close", tab=tab)
    page.goto(f"{site.url}/top")
    _frames(page)
    return page


def _frames(page, timeout: float = 10) -> dict[str, int]:
    """The tab's frames by the name in their URL (top, same, away), waited for."""
    end = time.monotonic() + timeout
    while True:
        found = {"top": 0}
        for frame in page.worker.call("frames", tab=page.tab):
            for name in ("same", "away"):
                if f"name={name}" in frame["url"]:
                    found[name] = frame["frame"]
        if len(found) == 3 or time.monotonic() > end:
            return found
        time.sleep(0.1)


def _in(page, frame: int, expression: str):
    return script.unwrap(page.worker.call("cdp.eval", tab=page.tab, frame=frame, code=wrap(expression)))


def test_user_scripts_off_the_eval_op_can_t_run_page_code_under_this_csp(page):
    with pytest.raises(PortError, match="user scripts are off"):
        script.unwrap(page.worker.call("eval", tab=page.tab, code=wrap("1 + 1")))


def test_page_code_reaches_each_frame_s_main_world_under_the_csp(page):
    frames = _frames(page)
    assert {name: _in(page, frame, "window.__mark") for name, frame in frames.items()} == {
        "top": "top", "same": "same", "away": "away"}


def test_runtime_is_never_turned_on(page):
    frames = _frames(page)
    for frame in frames.values():
        _in(page, frame, "document.title")
    time.sleep(0.3)  # several of the page's console calls
    assert [_in(page, frame, "window.__runtimeSeen") for frame in frames.values()] == [False, False, False]


def test_the_engine_held_in_memory_loads_in_every_frame(page):
    source = fill_engine.ENGINE.read_text()
    page.worker.call("cdp.keep", name="engine", source=source, sha256=script.hashlib.sha256(source.encode()).hexdigest())
    frames = _frames(page)
    for frame in frames.values():
        page.worker.call("engine.load", tab=page.tab, frame=frame)
    versions = {_in(page, frame, "FillEngine.version") for frame in frames.values()}
    assert len(versions) == 1 and next(iter(versions))


def test_an_engine_whose_sha256_differs_is_refused(worker):
    with pytest.raises(PortError, match="sha256 differs"):
        worker.call("cdp.keep", name="other", source="globalThis.x = 1;", sha256="0" * 64)


def test_an_early_script_runs_first_in_every_frame_of_the_tab_but_not_in_a_pop_up(page, site):
    page.worker.call("cdp.script", tab=page.tab, id="early", source="window.__applyEarly = true;")
    try:
        page.goto(f"{site.url}/top")
        frames = _frames(page)
        assert [_in(page, frame, "window.__earlyFirst") for frame in frames.values()] == [True, True, True]
        assert page.worker.call("cdp.eval", tab=page.tab, gesture=True,
                                code=f"window.open({json.dumps(site.url + '/frame?name=popup')}) ? 'opened' : 'blocked'") == "opened"
        end = time.monotonic() + 10
        while not (popup := next((t for t in page.worker.call("tabs.query") if "name=popup" in t["url"]), None)):
            assert time.monotonic() < end, "no pop-up opened"
            time.sleep(0.1)
        time.sleep(0.5)
        popped = script.unwrap(page.worker.call("cdp.eval", tab=popup["tab"], code=wrap("window.__earlyFirst")))
        assert popped is False  # outside the tab's session: the guards stay registered content scripts
    finally:
        page.worker.call("cdp.unscript", tab=page.tab, id="early")


@pytest.mark.parametrize("form", ["lever-immuta"])
def test_a_saved_form_fills_the_same_through_the_debugger(form, monkeypatch):
    if not (demo.SAVED_FORMS / form / "page.har").exists():
        pytest.skip("needs the Fill engine's saved forms (git submodule update --init)")
    monkeypatch.delenv(script.EXEC, raising=False)
    plain = demo.fill(form, kind="testing")
    monkeypatch.setenv(script.EXEC, "debugger")
    debugged = demo.fill(form, kind="testing")

    def same(lines):
        return [line.split(" at http", 1)[0] if " at http" in line else line for line in lines]

    assert same(debugged) == same(plain)
