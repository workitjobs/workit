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
    dead: the sign-in, first run, the student page with the queue and the usage line, and Settings with its Report a
    Problem form."""
    from apply import dashboard

    monkeypatch.setattr(dashboard, "ThreadingHTTPServer", None)
    errors = []
    answers = {
        "first_run": {"step": "seed", "lines": ["Now: Turn on Developer mode."], "running": True, "waiting": True,
                      "failed": ""},
        "queue": [{"url": "https://jobs.lever.co/acme/1", "company": "Acme", "title": "Intern"}],
        "matches": [],  # Find jobs, where the page opens (KAN-882): a list, as Bridge.matches answers
        "usage": {"used": 72000, "cap": 80000, "resets_at": "2026-11-16T00:00:00Z"},
        "status": {"running": False, "said": ""},
        "settings_state": {"workers": 3, "automatic": 2, "notices": True, "claude": {
            "best": True, "login": "your setup token in Keychain", "dropped": "Opus paused: near the 5-hour limit."}},
        "review_report": {"parts": ["Your words"]},
        "send_report": {"said": "Sent. WorkIt keeps your report until its problem is fixed, then deletes it."},
    }
    with Dashboard(0, OneFrame(), serve=False) as board, sync_playwright() as playwright:
        bridge = Bridge(board, WorkIt(workit.LIVE))  # the page's own requests (its state poll) get real answers
        browser = playwright.chromium.launch()
        pages = []
        for html in (app_window.SIGN_IN, app_window.FIRST_RUN, app_window.student_page(board), app_window.SETTINGS):
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
        queue.click("text=Your queue · paste a link")  # the queue is a click away from Find jobs
        queue.wait_for_selector("text=What should we apply to?", timeout=5000)
        queue.wait_for_selector("text=Intern", timeout=5000)
        assert queue.is_visible("text=Start applying to 1 job")
        # The Usage cap in words, never in tokens.
        queue.wait_for_selector("text=You're close to today's limit.", timeout=5000)
        assert "72" not in queue.inner_text("main")
        assert queue.is_visible("text=Settings")
        # An edit from the page, with the token it was served, gets past the route's check to the route itself.
        sent = """token => fetch('/fill-again', {method: 'POST', headers: {'X-Apply-Token': token},
                                                  body: JSON.stringify({id: 'tile-0'})}).then(r => r.status)"""
        assert queue.evaluate(sent, "not the token") == 403
        assert queue.evaluate(f"({sent})(window.APPLY_TOKEN)") != 403
        settings.wait_for_function("document.getElementById('workers').value === '3'", timeout=5000)
        assert settings.inner_text("#workers-auto") == "Automatic (2 for this Mac)"
        assert settings.locator("#workers option").all_inner_texts()[1:] == ["1", "2", "3", "4"]  # four by choice
        assert settings.is_visible("#notices") and not settings.is_visible("#remove-sure")
        assert settings.is_checked("#best")
        assert settings.inner_text("#claude-login") == "Claude signs in with your setup token in Keychain."
        assert settings.inner_text("#claude-dropped") == "Opus paused: near the 5-hour limit."
        settings.click("#remove")
        assert settings.is_visible("#remove-sure")  # a second press removes: one press never does
        # Report a problem: what goes is shown before Send Report, and a changed answer is shown again first.
        settings.fill("#report-note", "The window froze.")
        settings.click("#report button")
        settings.wait_for_selector("#report-send", state="visible", timeout=5000)
        assert settings.inner_text("#report-parts") == "Your words"
        settings.fill("#report-note", "The window froze twice.")
        assert not settings.is_visible("#report-send")
        settings.click("#report button")
        settings.click("#report-send")
        settings.wait_for_function("document.getElementById('report-said').textContent.startsWith('Sent.')",
                                   timeout=5000)
        assert not settings.is_visible("#report-send") and settings.input_value("#report-note") == ""
        browser.close()
    assert errors == []


def test_report_a_problem_on_an_applications_row_reviews_and_sends_with_its_id(monkeypatch):
    """Fault: the card's report reviewed without its Application's id, sent with no Review Report or under another
    id, or a changed answer sent without being shown again."""
    from apply import dashboard

    monkeypatch.setattr(dashboard, "ThreadingHTTPServer", None)
    answers = {"review_report": {"parts": ["Your words", "Which application: Acme, Intern"]},
               "send_report": {"said": "Sent. WorkIt keeps your report until its problem is fixed, then deletes it."}}
    calls, errors = [], []
    with Dashboard(1, OneFrame(), serve=False) as board, sync_playwright() as playwright:
        board.update(0, company="Acme", role="Intern", application_id="gh-1", status="failed",
                     posting_url="https://boards.greenhouse.io/acme/jobs/1")
        bridge = Bridge(board, WorkIt(workit.LIVE))

        def call(name, args):
            if name == "request":
                return bridge.request(*args)
            if name in answers:
                calls.append([name, *args])
            return answers.get(name, {})

        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.route("**/*", lambda route: route.abort())
        page.expose_function("__bridge", call)
        page.set_content(app_window.student_page(board), wait_until="domcontentloaded")
        page.evaluate(PYWEBVIEW)
        page.click("text=Report a problem", timeout=5000)  # the "Didn't go through" row's
        page.select_option("select", "answer")  # apply.report's categories, put in the page
        page.fill("textarea", "It picked the wrong school.")
        page.click("text=Review Report")
        page.wait_for_selector("text=Which application: Acme, Intern", timeout=5000)
        page.fill("textarea", "It picked the wrong school twice.")
        assert not page.is_visible("text=Send Report")  # a changed answer is shown again first
        page.click("text=Review Report")
        page.click("text=Send Report")
        page.wait_for_selector("text=Sent. WorkIt keeps your report", timeout=5000)
        browser.close()
    assert calls == [["review_report", "answer", "It picked the wrong school.", False, "gh-1", True],
                     ["review_report", "answer", "It picked the wrong school twice.", False, "gh-1", True],
                     ["send_report", "gh-1"]]
    assert errors == []


def test_a_logo_that_fails_to_load_falls_back_to_the_next_source_then_to_initials(monkeypatch):
    """Fault: a broken image in a queue row, or the initials kept when the scraper's logo loads (KAN-871)."""
    import base64

    from apply import dashboard

    monkeypatch.setattr(dashboard, "ThreadingHTTPServer", None)
    logo = "https://logos.example/acme.png"
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
    queue = [{"url": "https://jobs.lever.co/acme/1", "company": "Acme", "title": "Intern", "logo_url": logo,
              "company_domain": "acme.com"},
             {"url": "https://jobs.lever.co/beta/1", "company": "Beta", "title": "Analyst", "logo_url": None,
              "company_domain": "beta.com"}]
    with Dashboard(0, OneFrame(), serve=False) as board, sync_playwright() as playwright:
        bridge = Bridge(board, WorkIt(workit.LIVE))
        browser = playwright.chromium.launch()
        page = browser.new_page()
        # Brandfetch (and every other host) unreachable; only the scraper's logo for Acme loads.
        page.route("**/*", lambda route: route.fulfill(body=png, content_type="image/png") if route.request.url == logo
                   else route.abort())
        page.expose_function("__bridge", lambda name, args: bridge.request(*args) if name == "request"
                             else {"queue": queue, "matches": [], "status": {"running": False, "said": ""}}.get(name, {}))
        page.set_content(app_window.student_page(board), wait_until="domcontentloaded")
        page.evaluate(PYWEBVIEW)
        page.click("text=Your queue · paste a link")  # the page opens on Find jobs (KAN-882)
        page.wait_for_selector("text=Analyst", timeout=5000)
        page.wait_for_function(f"""[...document.images].some(i => i.src === {logo!r} && i.naturalWidth > 0
                                   && !i.className.includes('opacity-0'))""", timeout=5000)
        page.wait_for_function("document.images.length === 1", timeout=5000)  # Beta's failed Brandfetch icon: gone
        beta = page.locator("label", has_text="Analyst")
        assert beta.locator("span[aria-hidden]").inner_text() == "B"
        browser.close()
