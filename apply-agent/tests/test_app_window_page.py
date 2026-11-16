"""The window's page shim (app_window.SHIM) in Chromium, with Playwright in pywebview's place: the page's fetch, its
/frames stream and its file links reach the real Bridge (KAN-858). The app runs it in WKWebView. Opens Chromium: run
on a Mac, not in CI."""

from playwright.sync_api import sync_playwright
from test_app_window import JPEG, OneFrame

from apply import app_window, workit
from apply.app_window import Bridge
from apply.dashboard import Dashboard
from apply.workit import WorkIt

# pywebview's window.pywebview.api, played by one exposed function, put in once the page has loaded, as pywebview does.
PYWEBVIEW = """window.pywebview = {api: new Proxy({}, {get: (_, name) => (...args) => window.__bridge(name, args)})};
dispatchEvent(new Event('pywebviewready'));"""


def test_the_pages_requests_frames_and_file_links_go_through_the_bridge(tmp_path, monkeypatch):
    """Fault: the shim leaves a request, the /frames stream or a file link on the page's own (no) server."""
    monkeypatch.setattr(app_window, "FRAMES_WAIT", 0.1)
    sent = tmp_path / "resume.pdf"
    sent.write_bytes(b"%PDF-1.4")
    opened = []
    with Dashboard(1, OneFrame(), serve=False) as board, sync_playwright() as playwright:
        board.update(0, files=[{"label": "Resume", "path": str(sent)}])
        bridge = Bridge(board, WorkIt(workit.LIVE), opened.append)
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.route("**/*", lambda route: route.abort())  # the page's web font: no test reaches past loopback
        page.expose_function("__bridge", lambda name, args: getattr(bridge, name)(*args))
        page.set_content(app_window.page(board), wait_until="domcontentloaded")
        page.evaluate(PYWEBVIEW)

        assert "tiles" in page.evaluate("fetch('/state').then(r => r.json())")
        assert page.evaluate("fetch('/start', {method: 'POST', body: TOKEN}).then(r => r.status)") == 204
        # The page's own reader of /frames draws tile 0's frame.
        page.wait_for_function("document.getElementById('frame-0').src.startsWith('blob:')", timeout=5000)
        size = page.evaluate("fetch(document.getElementById('frame-0').src).then(r => r.arrayBuffer()).then(b => b.byteLength)")
        assert size == len(JPEG)
        page.evaluate("""() => { const a = document.createElement('a'); a.href = '/file/0/0'; a.textContent = 'View';
                                 document.body.append(a); a.click(); }""")
        page.wait_for_timeout(300)
        assert opened == [sent.as_uri()]
        browser.close()


def test_the_apps_own_pages_run_without_a_script_error(monkeypatch):
    """Fault: a script error in a page of the app's own (a line break inside a string, say), which leaves its buttons
    dead: the sign-in, first run, the queue with the usage line, and Settings."""
    from apply import dashboard

    monkeypatch.setattr(dashboard, "ThreadingHTTPServer", None)
    errors = []
    answers = {
        "first_run": {"step": "seed", "lines": ["Now: Turn on Developer mode."], "running": True, "waiting": True,
                      "failed": ""},
        "queue": [{"url": "https://jobs.lever.co/acme/1", "company": "Acme", "title": "Intern"}],
        "usage": {"used": 1200, "cap": 80000, "resets_at": "2026-11-16T00:00:00Z"},
        "status": {"running": False, "said": ""},
        "settings_state": {"workers": 3, "notices": True},
    }
    with Dashboard(0, OneFrame(), serve=False) as board, sync_playwright() as playwright:
        bridge = Bridge(board, WorkIt(workit.LIVE))  # the page's own requests (its state poll) get real answers
        browser = playwright.chromium.launch()
        pages = []
        for html in (app_window.SIGN_IN, app_window.FIRST_RUN, app_window.page(board, panel=True, usage=True),
                     app_window.SETTINGS):
            page = browser.new_page()  # a page each, as the window loads each one anew
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.route("**/*", lambda route: route.abort())
            page.expose_function("__bridge", lambda name, args: bridge.request(*args) if name == "request"
                                 else answers.get(name, {}))
            page.set_content(html, wait_until="domcontentloaded")
            page.evaluate(PYWEBVIEW)
            pages.append(page)
        first_run, queue, settings = pages[1], pages[2], pages[3]
        first_run.wait_for_function("!document.getElementById('seed').hidden", timeout=5000)
        assert first_run.inner_text("#seed-lines") == "Now: Turn on Developer mode."
        assert first_run.is_visible("#seed-again") and not first_run.is_visible("#seed-start")
        queue.wait_for_function("document.querySelectorAll('#queue input').length === 1", timeout=5000)
        assert queue.inner_text("#queue").strip() == "Acme: Intern"
        queue.wait_for_function("document.getElementById('usage').textContent !== ''", timeout=5000)
        assert queue.inner_text("#usage") == "Model use today: 1,200 of 80,000 tokens"
        # Fault: the queue's Start shares an id with the window's own Start, whose state poll hides it each second.
        queue.wait_for_timeout(2500)
        assert queue.is_visible("#queue-start")
        settings.wait_for_function("document.getElementById('workers').value === '3'", timeout=5000)
        assert settings.is_visible("#notices") and not settings.is_visible("#remove-sure")
        settings.click("#remove")
        assert settings.is_visible("#remove-sure")  # a second press removes: one press never does
        browser.close()
    assert errors == []
